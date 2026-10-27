const { DatabaseSync } = require("node:sqlite");
const db = new DatabaseSync("/app/server/data/freeapi.db", { readOnly: true });
const now = Date.now();
const MIN = 60_000;
const DAY = 86_400_000;

const all = (sql, ...args) => db.prepare(sql).all(...args);
const get = (sql, ...args) => db.prepare(sql).get(...args);

const settings = Object.fromEntries(all("SELECT key, value FROM settings").map((r) => [r.key, r.value]));
const keys = all(
  "SELECT id, platform, label, status, enabled, base_url, model_scope_json, monthly_request_cap, monthly_token_cap FROM api_keys ORDER BY id"
);
const models = all(
  "SELECT platform, model_id, display_name, rpm_limit, rpd_limit, tpm_limit, tpd_limit, key_id FROM models WHERE enabled = 1"
);

function parseScope(value) {
  if (!value) return null;
  try {
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) return null;
    const ids = parsed.filter((v) => typeof v === "string" && v.length > 0);
    return ids.length ? new Set(ids) : null;
  } catch {
    return null;
  }
}

const eligible = new Map();
const baseUrlByKey = new Map();
for (const key of keys) {
  baseUrlByKey.set(key.id, key.base_url);
  if (key.enabled !== 1 || (key.status !== "healthy" && key.status !== "unknown")) continue;
  const list = eligible.get(key.platform) || [];
  list.push({ ...key, scope: parseScope(key.model_scope_json) });
  eligible.set(key.platform, list);
}

const usageRows = all(
  `SELECT platform, model_id, key_id,
     SUM(CASE WHEN kind = 'request' AND created_at_ms > ? THEN 1 ELSE 0 END) AS rpm,
     SUM(CASE WHEN kind = 'request' THEN 1 ELSE 0 END) AS rpd,
     SUM(CASE WHEN kind = 'tokens' AND created_at_ms > ? THEN tokens ELSE 0 END) AS tpm,
     SUM(CASE WHEN kind = 'tokens' THEN tokens ELSE 0 END) AS tpd
   FROM rate_limit_usage
   WHERE created_at_ms > ?
   GROUP BY platform, model_id, key_id`,
  now - MIN,
  now - MIN,
  now - DAY
);
const usage = new Map();
for (const row of usageRows) {
  usage.set(`${row.platform}\u0000${row.model_id}\u0000${row.key_id}`, row);
}

const WINDOWS = [
  ["RPM", "rpm", "rpm_limit"],
  ["RPD", "rpd", "rpd_limit"],
  ["TPM", "tpm", "tpm_limit"],
  ["TPD", "tpd", "tpd_limit"],
];

function windowStats(model, keyId) {
  const row = usage.get(`${model.platform}\u0000${model.model_id}\u0000${keyId}`) || {
    rpm: 0,
    rpd: 0,
    tpm: 0,
    tpd: 0,
  };
  return WINDOWS.map(([id, usedKey, limitKey]) => ({
    id,
    used: Number(row[usedKey] || 0),
    limit: model[limitKey] == null ? null : Number(model[limitKey]),
  }));
}

function pressureOf(windows) {
  let worst = 0;
  for (const w of windows) {
    if (w.limit == null || w.limit <= 0) continue;
    worst = Math.max(worst, w.used / w.limit);
  }
  return worst;
}

let binding = null;
const routableModels = new Set();
for (const model of models) {
  const limits = WINDOWS.map(([, , limitKey]) => model[limitKey]);
  if (limits.every((value) => value == null || value <= 0)) continue;
  const pool = eligible.get(model.platform) || [];
  let best = null;
  for (const key of pool) {
    if (key.scope && !key.scope.has(model.model_id)) continue;
    if (model.platform === "custom" && model.key_id != null) {
      const modelBase = baseUrlByKey.get(model.key_id) ?? null;
      if (modelBase == null ? key.id !== model.key_id : key.base_url !== modelBase) continue;
    }
    routableModels.add(`${model.platform}\u0000${model.model_id}`);
    const windows = windowStats(model, key.id);
    const pressure = pressureOf(windows);
    if (best === null || pressure < best.pressure) {
      best = { pressure, key, windows };
    }
    if (best.pressure === 0) break;
  }
  if (best === null) continue;
  const candidate = {
    platform: model.platform,
    model_id: model.model_id,
    display_name: model.display_name || model.model_id,
    key: best.key,
    pressure: Math.min(1, best.pressure),
    raw_pressure: best.pressure,
    windows: best.windows,
  };
  if (
    binding === null ||
    candidate.pressure > binding.pressure ||
    (candidate.pressure === binding.pressure && candidate.raw_pressure > binding.raw_pressure)
  ) {
    binding = candidate;
  }
}

if (binding && binding.pressure === 0) {
  // Nothing is above zero: still show a useful window. Prefer the busiest
  // limited model instead of the first catalogue row.
  let busiest = null;
  for (const model of models) {
    if (WINDOWS.every(([, , limitKey]) => model[limitKey] == null || model[limitKey] <= 0)) continue;
    const pool = eligible.get(model.platform) || [];
    for (const key of pool) {
      if (key.scope && !key.scope.has(model.model_id)) continue;
      const windows = windowStats(model, key.id);
      const count = windows.reduce((sum, w) => sum + w.used, 0);
      if (busiest === null || count > busiest.count) {
        busiest = {
          count,
          platform: model.platform,
          model_id: model.model_id,
          display_name: model.display_name || model.model_id,
          key,
          pressure: 0,
          raw_pressure: 0,
          windows,
        };
      }
    }
  }
  if (busiest) binding = busiest;
}

if (binding) {
  const preferred = binding.pressure > 0 ? binding.windows : [binding.windows[1], binding.windows[3], binding.windows[0], binding.windows[2]];
  let worst = null;
  for (const w of preferred) {
    if (w.limit == null || w.limit <= 0) continue;
    if (worst === null || w.used / w.limit > worst.used / worst.limit) worst = w;
  }
  binding.window = worst;
}

const since = new Date(now - DAY).toISOString().slice(0, 19).replace("T", " ");
const day = get(
  `SELECT COUNT(*) AS n,
     SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS ok,
     SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errors,
     SUM(CASE WHEN status = 'canceled' THEN 1 ELSE 0 END) AS canceled,
     SUM(input_tokens) AS tin, SUM(output_tokens) AS tout,
     AVG(CASE WHEN status = 'success' THEN latency_ms END) AS latency,
     MAX(created_at) AS last
   FROM requests WHERE created_at >= ?`,
  since
);
const latencies = all(
  "SELECT latency_ms FROM requests WHERE created_at >= ? AND status = 'success' ORDER BY latency_ms",
  since
).map((r) => r.latency_ms || 0);
const p95 = latencies.length ? latencies[Math.min(latencies.length - 1, Math.floor(latencies.length * 0.95))] : null;

const providers = all(
  `SELECT platform, COUNT(*) AS n,
     SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS ok,
     SUM(input_tokens) AS tin, SUM(output_tokens) AS tout,
     AVG(CASE WHEN status = 'success' THEN latency_ms END) AS latency
   FROM requests WHERE created_at >= ? GROUP BY platform ORDER BY n DESC`,
  since
);

const month = new Date(now).toISOString().slice(0, 7);
const monthlyRows = all("SELECT * FROM key_monthly_usage WHERE month = ?", month);
const monthlyByKey = new Map(monthlyRows.map((r) => [r.key_id, r]));
const monthly = {
  requests: monthlyRows.reduce((sum, r) => sum + r.requests, 0),
  tokens: monthlyRows.reduce((sum, r) => sum + r.tokens, 0),
};

const cooldowns = all(
  "SELECT platform, model_id, key_id, expires_at_ms, source FROM rate_limit_cooldowns WHERE expires_at_ms > ? ORDER BY expires_at_ms",
  now
);

const lastError = get(
  "SELECT created_at, platform, model_id, status, error FROM requests WHERE status IN ('error', 'canceled') ORDER BY id DESC LIMIT 1"
);

const modelsWithLimits = models.filter((m) =>
  WINDOWS.some(([, , limitKey]) => m[limitKey] != null && m[limitKey] > 0)
).length;
const platforms = new Set(keys.filter((k) => k.enabled === 1).map((k) => k.platform));

const toEpoch = (value) => (value ? Date.parse(value.replace(" ", "T") + "Z") : null);

const output = {
  generated_at: Math.round(now / 1000),
  online: true,
  catalog: settings.catalog_applied_version || null,
  pressure: binding
    ? {
        pct: Math.round(binding.pressure * 1000) / 10,
        raw_pct: Math.round(binding.raw_pressure * 1000) / 10,
        model: binding.display_name,
        model_id: binding.model_id,
        platform: binding.platform,
        key_id: binding.key.id,
        key_label: binding.key.label,
        window: binding.window ? binding.window.id : null,
        used: binding.window ? binding.window.used : null,
        limit: binding.window ? binding.window.limit : null,
        windows: binding.windows,
        limited_models: routableModels.size,
      }
    : null,
  requests: {
    total: day.n || 0,
    ok: day.ok || 0,
    errors: day.errors || 0,
    canceled: day.canceled || 0,
    success_pct: day.n ? Math.round(((day.ok || 0) / day.n) * 1000) / 10 : null,
    tokens: (day.tin || 0) + (day.tout || 0),
    input_tokens: day.tin || 0,
    output_tokens: day.tout || 0,
    latency_ms: day.latency == null ? null : Math.round(day.latency),
    p95_ms: p95 == null ? null : Math.round(p95),
    last: toEpoch(day.last),
  },
  providers: providers.map((p) => ({
    platform: p.platform,
    requests: p.n,
    ok: p.ok || 0,
    success_pct: p.n ? Math.round(((p.ok || 0) / p.n) * 1000) / 10 : null,
    tokens: (p.tin || 0) + (p.tout || 0),
    latency_ms: p.latency == null ? null : Math.round(p.latency),
  })),
  monthly: {
    label: month,
    requests: monthly.requests,
    tokens: monthly.tokens,
    resets_at: null, // filled below
    keys: keys.map((key) => {
      const row = monthlyByKey.get(key.id);
      return {
        id: key.id,
        label: key.label,
        platform: key.platform,
        status: key.status,
        enabled: key.enabled,
        requests: row ? row.requests : 0,
        tokens: row ? row.tokens : 0,
        request_cap: key.monthly_request_cap > 0 ? key.monthly_request_cap : null,
        token_cap: key.monthly_token_cap > 0 ? key.monthly_token_cap : null,
      };
    }),
  },
  models: {
    enabled: models.length,
    with_limits: modelsWithLimits,
    routable_limits: routableModels.size,
    providers: platforms.size,
  },
  cooldowns: {
    count: cooldowns.length,
    next: cooldowns.length
      ? {
          platform: cooldowns[0].platform,
          model_id: cooldowns[0].model_id,
          expires_at: Math.round(cooldowns[0].expires_at_ms / 1000),
          source: cooldowns[0].source,
        }
      : null,
  },
  last_error: lastError
    ? {
        at: toEpoch(lastError.created_at),
        platform: lastError.platform,
        model_id: lastError.model_id,
        status: lastError.status,
        error: (lastError.error || "").slice(0, 140),
      }
    : null,
  totals: {
    requests: Number(settings.total_requests || 0),
    input_tokens: Number(settings.total_input_tokens || 0),
    output_tokens: Number(settings.total_output_tokens || 0),
  },
};

// Add one calendar month to the current month, not a fixed 32 days.
{
  const [y, m] = month.split("-").map(Number);
  const next = new Date(Date.UTC(y, m, 1));
  output.monthly.resets_at = Math.floor(next.getTime() / 1000);
}

console.log(JSON.stringify(output));

using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.Json;

namespace TokenMonitor.Windows;

public sealed record GaugePanelSection(string Title, IReadOnlyList<(string Key, string Value)> Rows);
public sealed record GaugeData(string Id, string Label, double? Percent, string Subtext, IReadOnlyList<(string Key, string Value)> Details, string? Note, IReadOnlyList<GaugePanelSection>? Sections = null);

public sealed class DataCollector
{
    private readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(8) };
    private readonly string _home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

    public async Task<IReadOnlyList<GaugeData>> CollectAllAsync(CancellationToken ct = default) => await Task.WhenAll(
        CollectClaudeAsync(ct), CollectCursorAsync(ct), CollectCodexAsync(ct), CollectFreeLlmApiAsync(ct));

    private async Task<GaugeData> CollectClaudeAsync(CancellationToken ct)
    {
        var empty = new GaugeData("claude", "Claude Code", null, "—", [], null);
        var oauth = await CollectClaudeOAuthAsync(empty, ct);
        if (oauth.Percent.HasValue) return oauth;
        var exe = FindExecutable("claude-monitor");
        if (exe is null) return oauth;
        try
        {
            using var doc = JsonDocument.Parse(await RunAsync(exe, "--once --output json", ct));
            var five = GetObject(doc.RootElement, "limits", "five_hour");
            var pct = GetDouble(five, "used_percentage"); var reset = GetDouble(five, "resets_at_epoch");
            var rows = new List<(string, string)> { ("Janela 5h", $"{Pct(pct)} · {Human(GetDouble(five, "tokens_used"))}/{Human(GetDouble(five, "token_limit"))} tok"), ("Reset 5h", Clock(reset)) };
            var week = GetObject(doc.RootElement, "limits", "seven_day");
            if (GetDouble(week, "used_percentage") is double wp) rows.Add(("Janela 7d", $"{wp:0.0}% · reset {Clock(GetDouble(week, "resets_at_epoch"))}"));
            var local = GetObject(doc.RootElement, "local");
            rows.Add(("Sessão", $"{GetDouble(local, "sent_messages") ?? 0:0} mensagens"));
            rows.Add(("Burn rate", $"{Human(GetDouble(local, "burn_rate_tokens_per_minute"))} tok/min"));
            rows.Add(("Pace", GetString(GetObject(doc.RootElement, "pace"), "label") ?? "—"));
            rows.Add(("Confiança", GetString(five, "confidence") ?? "—"));
            return new GaugeData("claude", "Claude Code", pct, ResetLabel(reset), rows, null);
        }
        catch (Exception ex) { return empty with { Note = $"claude-monitor falhou: {ex.Message}" }; }
    }

    private async Task<GaugeData> CollectClaudeOAuthAsync(GaugeData empty, CancellationToken ct)
    {
        var credentials = ReadClaudeCredentials();
        if (credentials is null) return empty with { Note = "credencial OAuth do Claude Code não encontrada" };
        if (credentials.Value.ExpiresAt is double expiry && expiry > 0 && expiry < DateTimeOffset.UtcNow.ToUnixTimeMilliseconds())
            return empty with { Note = "credencial OAuth do Claude Code expirada; execute claude no terminal para renovar" };

        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, "https://api.anthropic.com/api/oauth/usage");
            request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", credentials.Value.Token);
            request.Headers.TryAddWithoutValidation("anthropic-beta", "oauth-2025-04-20");
            request.Headers.Accept.ParseAdd("application/json");
            using var response = await _http.SendAsync(request, ct);
            if ((int)response.StatusCode == 401)
                return empty with { Note = "Claude recusou a credencial OAuth; execute claude no terminal para renovar" };
            if ((int)response.StatusCode == 429)
                return empty with { Note = "limite temporário da API do Claude; tente novamente em instantes" };
            response.EnsureSuccessStatusCode();

            using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
            var windows = ParseClaudeWindows(doc.RootElement);
            var primary = windows.FirstOrDefault(w => w.Kind is "session" or "five_hour");
            if (primary == default) primary = windows.FirstOrDefault();
            if (primary == default) return empty with { Note = "API do Claude respondeu sem janelas de uso" };

            var rows = windows.Select(w => ($"{ClaudeWindowLabel(w.Kind)}", $"{w.Percent:0.0}% · reset {Clock(w.Reset)}")).ToList();
            rows.Add(("Fonte", "Claude Code OAuth oficial"));
            return new GaugeData("claude", "Claude Code", primary.Percent, ResetLabel(primary.Reset), rows, null);
        }
        catch (HttpRequestException ex) { return empty with { Note = $"API OAuth do Claude indisponível: {ex.Message}" }; }
        catch (JsonException ex) { return empty with { Note = $"resposta da API do Claude inválida: {ex.Message}" }; }
        catch (Exception ex) { return empty with { Note = $"consulta OAuth do Claude falhou: {ex.Message}" }; }
    }

    private (string Token, double? ExpiresAt)? ReadClaudeCredentials()
    {
        var config = Path.Combine(_home, ".claude");
        foreach (var name in new[] { ".credentials.json", "credentials.json" })
        {
            var path = Path.Combine(config, name);
            if (!File.Exists(path)) continue;
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                var oauth = doc.RootElement.TryGetProperty("claudeAiOauth", out var nested) ? nested : doc.RootElement;
                var token = GetString(oauth, "accessToken");
                if (!string.IsNullOrWhiteSpace(token)) return (token, GetDouble(oauth, "expiresAt"));
            }
            catch (JsonException) { }
        }
        return null;
    }

    private static List<(string Kind, double Percent, double? Reset)> ParseClaudeWindows(JsonElement root)
    {
        var result = new List<(string Kind, double Percent, double? Reset)>();
        if (root.TryGetProperty("limits", out var limits) && limits.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in limits.EnumerateArray())
            {
                var kind = GetString(item, "kind");
                var percent = GetDouble(item, "percent");
                var reset = GetEpochSeconds(item, "resets_at");
                if (!string.IsNullOrWhiteSpace(kind) && percent is double p && reset.HasValue)
                    result.Add((kind, Math.Clamp(p, 0, 100), reset));
            }
        }
        foreach (var fallback in new[] { (Field: "five_hour", Kind: "session"), (Field: "seven_day", Kind: "seven_day") })
        {
            var item = GetObject(root, fallback.Field);
            var percent = GetDouble(item, "utilization");
            var reset = GetEpochSeconds(item, "resets_at");
            var duplicate = result.Any(w => fallback.Kind == "session"
                ? w.Kind is "session" or "five_hour"
                : w.Kind is "seven_day" or "weekly_all" or "weekly");
            if (percent is double p && reset.HasValue && !duplicate)
                result.Add((fallback.Kind, Math.Clamp(p, 0, 100), reset));
        }
        return result;
    }

    private static string ClaudeWindowLabel(string kind) => kind switch
    {
        "session" or "five_hour" => "Janela 5h",
        "seven_day" or "weekly_all" or "weekly" => "Janela 7d",
        "seven_day_opus" or "weekly_opus" => "Janela 7d Opus",
        _ => kind.Replace('_', ' ')
    };

    private async Task<GaugeData> CollectCursorAsync(CancellationToken ct)
    {
        var empty = new GaugeData("cursor", "Cursor", null, "—", [], null);
        var db = new[] { Path.Combine(_home, ".config", "Cursor", "User", "globalStorage", "state.vscdb"), Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Cursor", "User", "globalStorage", "state.vscdb") }.FirstOrDefault(File.Exists);
        if (db is null) return empty with { Note = "Cursor não instalado ou banco de sessão não encontrado" };
        try
        {
            var sqlite = FindExecutable("sqlite3") ?? FindAndroidSqlite();
            if (sqlite is null) return empty with { Note = "sqlite3 não encontrado para ler a sessão do Cursor" };
            var raw = await RunAsync(sqlite, $"-json \"{db}\" \"SELECT key, value FROM ItemTable WHERE key IN ('cursorAuth/accessToken','cursorAuth/stripeMembershipType');\"", ct);
            using var rowsJson = JsonDocument.Parse(raw); string? token = null; string? plan = null;
            foreach (var row in rowsJson.RootElement.EnumerateArray()) { var key = GetString(row, "key"); if (key == "cursorAuth/accessToken") token = GetString(row, "value"); if (key == "cursorAuth/stripeMembershipType") plan = GetString(row, "value"); }
            if (string.IsNullOrWhiteSpace(token)) return empty with { Note = "Cursor encontrado, mas sem sessão autenticada" };
            using var req = new HttpRequestMessage(HttpMethod.Post, "https://api2.cursor.sh/aiserver.v1.DashboardService/GetCurrentPeriodUsage"); req.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", token); req.Content = new StringContent("{}", System.Text.Encoding.UTF8, "application/json");
            using var response = await _http.SendAsync(req, ct); response.EnsureSuccessStatusCode(); using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
            var usage = GetObject(doc.RootElement, "planUsage"); var pct = GetDouble(usage, "totalPercentUsed"); var end = GetDouble(doc.RootElement, "billingCycleEnd");
            var details = new List<(string, string)> { ("Plano", (plan ?? "—").ToUpperInvariant()), ("Uso incluído", Pct(pct)), ("Auto / API", $"{GetDouble(usage, "autoPercentUsed") ?? 0:0.0}% · {GetDouble(usage, "apiPercentUsed") ?? 0:0.0}%"), ("Reset", ResetLabel(end.HasValue ? end.Value / 1000 : null)) };
            return new GaugeData("cursor", "Cursor", pct, end.HasValue ? DateTimeOffset.FromUnixTimeMilliseconds((long)end.Value).ToLocalTime().ToString("dd/MM") : "—", details, null);
        }
        catch (Exception ex) { return empty with { Note = $"API do Cursor indisponível: {ex.Message}" }; }
    }

    private async Task<GaugeData> CollectCodexAsync(CancellationToken ct)
    {
        var empty = new GaugeData("codex", "Codex", null, "—", [], null);
        var live = await CollectCodexLiveAsync(empty, ct);
        if (live.Percent.HasValue) return live;

        var root = Path.Combine(_home, ".codex", "sessions");
        if (!Directory.Exists(root)) return empty with { Note = "nenhuma sessão local do Codex encontrada" };
        try
        {
            // O Codex cria um rollout vazio ao iniciar uma conversa. Não basta
            // ler o arquivo mais recente: procuramos o último arquivo que
            // realmente contenha um evento token_count/rate_limits.
            foreach (var file in Directory.EnumerateFiles(root, "*.jsonl", SearchOption.AllDirectories).OrderByDescending(File.GetLastWriteTimeUtc))
            {
                if (new FileInfo(file).Length < 20) continue;
                var lines = await ReadSharedLinesAsync(file, ct);
                foreach (var line in lines.Reverse())
                {
                    using var doc = JsonDocument.Parse(line);
                    var limits = GetObject(GetObject(doc.RootElement, "payload"), "rate_limits");
                    if (limits.ValueKind != JsonValueKind.Object) continue;
                    var p = GetObject(limits, "primary"); var s = GetObject(limits, "secondary");
                    var pct = GetDouble(p, "used_percent"); var reset = GetDouble(p, "resets_in_seconds");
                    var details = new List<(string, string)> { ("Janela primária", $"{Pct(pct)} · {GetDouble(p, "window_minutes") ?? 0:0} min") };
                    if (s.ValueKind == JsonValueKind.Object) details.Add(("Janela secundária", $"{GetDouble(s, "used_percent") ?? 0:0.0}% · {GetDouble(s, "window_minutes") ?? 0:0} min"));
                    var info = GetObject(GetObject(doc.RootElement, "payload"), "info");
                    if (GetDouble(GetObject(info, "total_token_usage"), "total_tokens") is double total) details.Add(("Tokens na sessão", Human(total)));
                    if (GetDouble(info, "model_context_window") is double context) details.Add(("Contexto", Human(context)));
                    return new GaugeData("codex", "Codex", pct, ResetLabel(DateTimeOffset.UtcNow.ToUnixTimeSeconds() + (reset ?? 0)), details, null);
                }
            }
            return empty with { Note = "sessões do Codex encontradas, mas sem dados de limite" };
        }
        catch (Exception ex) { return empty with { Note = $"não foi possível ler o Codex: {ex.Message}" }; }
    }

    private async Task<GaugeData> CollectCodexLiveAsync(GaugeData empty, CancellationToken ct)
    {
        var credentials = ReadCodexCredentials();
        if (credentials is null) return empty with { Note = "sessão do Codex não encontrada em .codex\\auth.json" };

        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, "https://chatgpt.com/backend-api/wham/usage");
            request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", credentials.Value.AccessToken);
            request.Headers.TryAddWithoutValidation("ChatGPT-Account-Id", credentials.Value.AccountId);
            request.Headers.CacheControl = new System.Net.Http.Headers.CacheControlHeaderValue { NoCache = true, NoStore = true };
            request.Headers.UserAgent.ParseAdd("TokenMonitor/Windows");
            request.Headers.Accept.ParseAdd("application/json");
            using var response = await _http.SendAsync(request, ct);
            if ((int)response.StatusCode is 401 or 403)
                return empty with { Note = "Codex recusou a sessão; execute codex login novamente" };
            if ((int)response.StatusCode == 429)
                return empty with { Note = "limite temporário da API do Codex; tente novamente em instantes" };
            response.EnsureSuccessStatusCode();

            using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
            var rateLimit = GetObject(doc.RootElement, "rate_limit");
            var primary = ParseCodexWindow(rateLimit, "primary_window", "5h");
            var secondary = ParseCodexWindow(rateLimit, "secondary_window", "7d");
            var windows = new[] { primary, secondary }.Where(w => w.HasValue).Select(w => w!.Value).ToList();
            if (windows.Count == 0) return empty with { Note = "API do Codex respondeu sem janelas de uso" };

            var details = windows.Select(w => ($"Janela {w.Label}", $"{w.Percent:0.0}% · reset {Clock(w.Reset)}")).ToList();
            var plan = GetString(doc.RootElement, "plan_type");
            if (!string.IsNullOrWhiteSpace(plan)) details.Add(("Plano", plan));
            details.Add(("Fonte", "Codex OAuth oficial"));
            var current = windows[0];
            return new GaugeData("codex", "Codex", current.Percent, ResetLabel(current.Reset), details, null);
        }
        catch (HttpRequestException ex) { return empty with { Note = $"API do Codex indisponível: {ex.Message}" }; }
        catch (JsonException ex) { return empty with { Note = $"resposta da API do Codex inválida: {ex.Message}" }; }
        catch (Exception ex) { return empty with { Note = $"consulta do Codex falhou: {ex.Message}" }; }
    }

    private (string AccessToken, string AccountId)? ReadCodexCredentials()
    {
        var path = Path.Combine(_home, ".codex", "auth.json");
        if (!File.Exists(path)) return null;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(path));
            var tokens = GetObject(doc.RootElement, "tokens");
            var accessToken = GetString(tokens, "access_token");
            var accountId = GetString(tokens, "account_id");
            return !string.IsNullOrWhiteSpace(accessToken) && !string.IsNullOrWhiteSpace(accountId)
                ? (accessToken, accountId)
                : null;
        }
        catch (JsonException) { return null; }
    }

    private static (string Label, double Percent, double? Reset)? ParseCodexWindow(JsonElement rateLimit, string key, string fallbackLabel)
    {
        var window = GetObject(rateLimit, key);
        if (window.ValueKind != JsonValueKind.Object) return null;
        var percent = GetDouble(window, "used_percent");
        if (percent is not double used) return null;
        var reset = GetEpochSeconds(window, "reset_at");
        if (!reset.HasValue && GetDouble(window, "reset_after_seconds") is double after)
            reset = DateTimeOffset.UtcNow.ToUnixTimeSeconds() + after;
        return (WindowLabel(GetDouble(window, "limit_window_seconds") ?? 0, fallbackLabel), Math.Clamp(used, 0, 100), reset);
    }

    private static string WindowLabel(double seconds, string fallback) => seconds switch
    {
        >= 300 * 60 - 60 and <= 300 * 60 + 60 => "5h",
        >= 7 * 24 * 60 * 60 - 60 and <= 7 * 24 * 60 * 60 + 60 => "7d",
        _ => fallback
    };

    private async Task<GaugeData> CollectFreeLlmApiAsync(CancellationToken ct)
    {
        var empty = new GaugeData("freellmapi", "FreeLLMAPI", null, "—", [], null);
        var settings = FreeLlmApiSettings.Load();
        JsonElement catalog;
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, settings.MonitorUrl.TrimEnd('/') + "/models");
            if (!string.IsNullOrWhiteSpace(settings.ApiKey)) request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", settings.ApiKey);
            using var response = await _http.SendAsync(request, ct); response.EnsureSuccessStatusCode();
            using var catalogDoc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct));
            catalog = catalogDoc.RootElement.Clone();
        }
        catch (Exception ex) { return empty with { Note = $"FreeLLMAPI não respondeu em {settings.MonitorUrl}/models: {ex.Message}" }; }
        var usage = await GetJsonAsync(settings, "/usage", ct);
        var providers = await GetJsonAsync(settings, "/providers", ct);
        var docker = FindDocker();
        if (docker is null) return ProxyCatalogData(settings, catalog, "Docker não foi encontrado; mostrando os dados reais do proxy", usage, providers);
        try
        {
            var container = (await RunAsync(docker, "ps -q --filter label=com.docker.compose.service=freellmapi", ct)).Trim().Split('\n', StringSplitOptions.RemoveEmptyEntries).FirstOrDefault();
            if (string.IsNullOrWhiteSpace(container)) container = (await RunAsync(docker, "ps -q --filter name=freellmapi", ct)).Trim().Split('\n', StringSplitOptions.RemoveEmptyEntries).FirstOrDefault();
            if (string.IsNullOrWhiteSpace(container)) return ProxyCatalogData(settings, catalog, "container freellmapi não está em execução; mostrando os dados reais do proxy", usage, providers);
            var script = Path.Combine(AppContext.BaseDirectory, "FreeLlmApiQuery.js");
            var raw = await RunWithInputAsync(docker, $"exec -i {container} node -", await File.ReadAllTextAsync(script, ct), ct);
            var start = raw.IndexOf('{'); var end = raw.LastIndexOf('}');
            if (start < 0 || end <= start) throw new InvalidOperationException("resposta inválida do consultor");
            using var doc = JsonDocument.Parse(raw[start..(end + 1)]); var root = doc.RootElement; var pressure = GetObject(root, "pressure"); var requests = GetObject(root, "requests"); var monthly = GetObject(root, "monthly"); var models = GetObject(root, "models");
            var pct = GetDouble(pressure, "pct"); var win = GetString(pressure, "window") ?? "—"; var used = GetDouble(pressure, "used"); var limit = GetDouble(pressure, "limit");
            var details = new List<(string, string)>(); if (pressure.ValueKind == JsonValueKind.Object) { details.Add(("Pressão", $"{GetDouble(pressure, "raw_pct") ?? pct ?? 0:0.0}% · {GetString(pressure, "model") ?? "—"}")); details.Add(("Janela", $"{win} {Human(used)}/{Human(limit)} · {GetString(pressure, "key_label") ?? "—"}")); }
            details.Add(("Últimas 24h", $"{GetDouble(requests, "total") ?? 0:0} req · {GetDouble(requests, "success_pct") ?? 0:0.0}% sucesso")); details.Add(("Tokens 24h", Human(GetDouble(requests, "tokens")))); details.Add(("Mês", $"{GetDouble(monthly, "requests") ?? 0:0} req · {Human(GetDouble(monthly, "tokens"))} tok")); details.Add(("Modelos", $"{GetDouble(models, "enabled") ?? 0:0} · {GetDouble(models, "routable_limits") ?? 0:0} com limites")); details.Add(("Proxy", settings.BaseUrl));
            return new GaugeData("freellmapi", "FreeLLMAPI", pct, limit.HasValue ? $"{Human(used)}/{Human(limit)}" : "online", details, "Pressão = pior janela entre os modelos com chave elegível");
        }
        catch (Exception ex) { return empty with { Note = $"FreeLLMAPI online, mas a consulta Docker falhou: {ex.Message}" }; }
    }

    private static GaugeData ProxyCatalogData(FreeLlmApiSettings settings, JsonElement catalog, string note, JsonElement? usage, JsonElement? providers)
    {
        var rows = catalog.ValueKind == JsonValueKind.Object && catalog.TryGetProperty("data", out var data) && data.ValueKind == JsonValueKind.Array ? data.EnumerateArray().ToArray() : Array.Empty<JsonElement>();
        var available = rows.Count(row => GetBool(row, "available"));
        var details = new List<(string, string)> { ("Modelos", $"{available}/{rows.Length} disponíveis"), ("Modo", "auto / auto:fast"), ("Proxy", settings.BaseUrl) };
        var sections = new List<GaugePanelSection>();
        var pressure = new List<(string, string)> { ("Status", "online"), ("Pressão", "indisponível sem SQLite do Docker") };
        sections.Add(new GaugePanelSection("PRESSÃO DE LIMITE", pressure));
        if (usage is JsonElement usageRoot && usageRoot.ValueKind == JsonValueKind.Object)
        {
            var usageRows = new List<(string, string)> { ("Requisições", Number(usageRoot, "requests")), ("Tokens", Human(GetDouble(usageRoot, "tokens"))), ("Mês", GetString(usageRoot, "month") ?? "—"), ("Reset", GetString(usageRoot, "resetsAt") ?? "—") };
            sections.Add(new GaugePanelSection("USO DO MÊS", usageRows));
            if (usageRoot.TryGetProperty("byPlatform", out var byPlatform) && byPlatform.ValueKind == JsonValueKind.Array)
                sections.Add(new GaugePanelSection("POR PROVEDOR", byPlatform.EnumerateArray().Select(p => (GetString(p, "platform") ?? "—", $"{Number(p, "requests")} req · {Human(GetDouble(p, "tokens"))} tok")).ToArray()));
            if (usageRoot.TryGetProperty("byKey", out var byKey) && byKey.ValueKind == JsonValueKind.Array)
                sections.Add(new GaugePanelSection("CHAVES · OUTUBRO", byKey.EnumerateArray().Select(k => (GetString(k, "label") ?? GetString(k, "platform") ?? "—", $"{Number(k, "requests")} req · {Human(GetDouble(k, "tokens"))} tok")).ToArray()));
        }
        if (providers is JsonElement providerRoot && providerRoot.ValueKind == JsonValueKind.Object && providerRoot.TryGetProperty("providers", out var providerRows) && providerRows.ValueKind == JsonValueKind.Array)
            sections.Add(new GaugePanelSection("ROTEADOR", providerRows.EnumerateArray().Select(p => (GetString(p, "name") ?? GetString(p, "platform") ?? "—", GetString(p, "status") ?? "—")).ToArray()));
        return new GaugeData("freellmapi", "FreeLLMAPI", null, rows.Length > 0 ? $"{available}/{rows.Length}" : "online", details, note, sections);
    }

    private async Task<JsonElement?> GetJsonAsync(FreeLlmApiSettings settings, string path, CancellationToken ct)
    {
        try { using var request = new HttpRequestMessage(HttpMethod.Get, settings.MonitorUrl.TrimEnd('/') + path); if (!string.IsNullOrWhiteSpace(settings.ApiKey)) request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", settings.ApiKey); using var response = await _http.SendAsync(request, ct); response.EnsureSuccessStatusCode(); using var doc = JsonDocument.Parse(await response.Content.ReadAsStringAsync(ct)); return doc.RootElement.Clone(); }
        catch { return null; }
    }

    private static async Task<string> RunAsync(string file, string args, CancellationToken ct)
    {
        using var p = new Process { StartInfo = new ProcessStartInfo(file, args) { UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true } }; p.Start(); var output = await p.StandardOutput.ReadToEndAsync(ct); await p.WaitForExitAsync(ct); if (p.ExitCode != 0) throw new InvalidOperationException((await p.StandardError.ReadToEndAsync(ct)).Trim()); return output;
    }
    private static async Task<string> RunWithInputAsync(string file, string args, string input, CancellationToken ct)
    {
        using var p = new Process { StartInfo = new ProcessStartInfo(file, args) { UseShellExecute = false, RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true } };
        p.Start(); await p.StandardInput.WriteAsync(input.AsMemory(), ct); p.StandardInput.Close(); var output = await p.StandardOutput.ReadToEndAsync(ct); await p.WaitForExitAsync(ct); if (p.ExitCode != 0) throw new InvalidOperationException((await p.StandardError.ReadToEndAsync(ct)).Trim()); return output;
    }
    private static async Task<string[]> ReadSharedLinesAsync(string file, CancellationToken ct)
    {
        await using var stream = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete, 64 * 1024, useAsync: true);
        // Os rollouts podem estar sendo escritos pelo Codex; o compartilhamento
        // explícito permite ler o snapshot sem disputar o lock do processo.
        if (stream.Length > 500_000) stream.Seek(-500_000, SeekOrigin.End);
        using var reader = new StreamReader(stream);
        var text = await reader.ReadToEndAsync(ct);
        return text.Split(new[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries);
    }
    private string? FindExecutable(string name) => Environment.GetEnvironmentVariable("PATH")?.Split(Path.PathSeparator).Select(p => Path.Combine(p, name + (OperatingSystem.IsWindows() ? ".exe" : ""))).FirstOrDefault(File.Exists);
    private string? FindAndroidSqlite() { var p = Path.Combine(_home, "AppData", "Local", "Android", "Sdk", "platform-tools", "sqlite3.exe"); return File.Exists(p) ? p : null; }
    private string? FindDocker() => new[] { FindExecutable("docker"), @"C:\Program Files\Docker\Docker\resources\bin\docker.exe", Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Docker", "Docker", "resources", "bin", "docker.exe") }.FirstOrDefault(p => !string.IsNullOrWhiteSpace(p) && File.Exists(p));
    private static JsonElement GetObject(JsonElement e, params string[] keys) { foreach (var key in keys) { if (e.ValueKind != JsonValueKind.Object || !e.TryGetProperty(key, out e)) return default; } return e; }
    private static string? GetString(JsonElement e, string key) => e.ValueKind == JsonValueKind.Object && e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
    private static bool GetBool(JsonElement e, string key) => e.ValueKind == JsonValueKind.Object && e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.True;
    private static double? GetDouble(JsonElement e, string key) => e.ValueKind == JsonValueKind.Object && e.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.Number && v.TryGetDouble(out var n) ? n : null;
    private static double? GetEpochSeconds(JsonElement e, string key)
    {
        if (e.ValueKind != JsonValueKind.Object || !e.TryGetProperty(key, out var value)) return null;
        if (value.ValueKind == JsonValueKind.Number && value.TryGetDouble(out var number)) return number > 1_000_000_000_000 ? number / 1000 : number;
        if (value.ValueKind == JsonValueKind.String && DateTimeOffset.TryParse(value.GetString(), out var date)) return date.ToUnixTimeSeconds();
        return null;
    }
    private static string Pct(double? n) => n.HasValue ? $"{n.Value:0.0}%" : "—";
    private static string Number(JsonElement e, string key) => GetDouble(e, key)?.ToString("0") ?? "0";
    private static string Human(double? n) => !n.HasValue ? "—" : n.Value >= 1_000_000 ? $"{n.Value / 1_000_000:0.0}M" : n.Value >= 1000 ? $"{n.Value / 1000:0.0}k" : $"{n.Value:0}";
    private static string Clock(double? n) => n.HasValue && n > 0 ? DateTimeOffset.FromUnixTimeSeconds((long)n.Value).ToLocalTime().ToString("HH:mm") : "—";
    private static string ResetLabel(double? n) => Clock(n);
}

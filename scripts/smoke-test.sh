#!/usr/bin/env bash
# Local smoke test — run before committing or publishing any change.
#
#   ./scripts/smoke-test.sh            # warnings allowed
#   ./scripts/smoke-test.sh --strict   # fail if the user install is outdated
set -uo pipefail

cd "$(dirname "$0")/.."

STRICT=0
[[ "${1:-}" == "--strict" ]] && STRICT=1

PASS=0
FAIL=0
WARN=0

ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; PASS=$((PASS + 1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; FAIL=$((FAIL + 1)); }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; WARN=$((WARN + 1)); }

echo "tokenmonitor — smoke test"
echo "== 1/6  sintaxe e dependências"
if python3 -m py_compile src/tokenmon.py; then
  ok "src/tokenmon.py compila"
else
  bad "erro de sintaxe em src/tokenmon.py"
fi

if python3 - <<'PY'
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
import cairo
from gi.repository import Gdk, Gtk, Pango  # noqa: F401
assert Gtk.get_major_version() == 4
print(f"Gtk {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}")
PY
then
  ok "imports GTK 4 / Pycairo"
else
  bad "imports GTK 4 / Pycairo indisponíveis"
fi

if command -v wmctrl >/dev/null 2>&1; then
  ok "wmctrl disponível"
else
  bad "wmctrl ausente (necessário para always-on-top e geometria)"
fi

echo "== 2/6  coleta de dados (headless)"
if python3 - <<'PY'
import importlib.util

spec = importlib.util.spec_from_file_location("tokenmon_smoke", "src/tokenmon.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

res = mod.collect_all()
by_id = {item.get("id"): item for item in res}
expected = ("claude", "cursor", "codex")
missing = [key for key in expected if key not in by_id]

for key in expected:
    r = by_id.get(key) or {}
    label = r.get("label", key)
    pct = r.get("pct")
    if pct is None:
        print(f"  · {label}: sem dados ({r.get('note') or '—'})")
    else:
        print(f"  · {label}: {pct:.1f}% · reset {r.get('sub', '—')}")

if missing:
    raise SystemExit(f"adaptadores ausentes: {missing}")
PY
then
  ok "três adaptadores responderam"
else
  bad "falha na coleta de dados"
fi

echo "== 3/6  assets do README"
missing_assets=0
while IFS= read -r asset; do
  if [[ ! -f "$asset" ]]; then
    bad "asset ausente: $asset"
    missing_assets=1
  fi
done < <(grep -oE 'docs/[A-Za-z0-9_-]+\.(png|svg)' README.md | sort -u)
[[ $missing_assets -eq 0 ]] && ok "assets referenciados existem"

if python3 -c "import PIL" >/dev/null 2>&1; then
  if python3 - <<'PY'
from PIL import Image
import glob
for path in sorted(glob.glob("docs/*.png")):
    with Image.open(path) as im:
        im.verify()
print(len(glob.glob("docs/*.png")), "PNGs válidos")
PY
  then
    ok "PNGs de documentação válidos"
  else
    bad "PNG de documentação inválido"
  fi
else
  warn "Pillow não instalado — validação de PNG ignorada"
fi

echo "== 4/6  empacotamento .deb"
if make deb >/dev/null 2>&1; then
  ok "make deb"
  DEB=$(ls -t dist/tokenmonitor_*.deb 2>/dev/null | head -1)
  if [[ -n "${DEB:-}" ]]; then
    ok "pacote gerado: $DEB"
    TMP=$(mktemp -d)
    if dpkg-deb -x "$DEB" "$TMP" 2>/dev/null; then
      if cmp -s src/tokenmon.py "$TMP/usr/lib/tokenmonitor/tokenmon.py"; then
        ok "código empacotado idêntico ao src/"
      else
        bad "código empacotado difere de src/tokenmon.py"
      fi
    else
      bad "não foi possível extrair o pacote"
    fi
    rm -rf "$TMP"
    if grep -q '^Architecture: all' <(dpkg-deb -f "$DEB") 2>/dev/null; then
      ok "Architecture: all"
    else
      warn "Architecture diferente de 'all'"
    fi
  else
    bad "nenhum .deb encontrado em dist/"
  fi
else
  bad "falha ao construir o .deb"
fi

echo "== 5/6  instalação de usuário"
if cmp -s src/tokenmon.py "$HOME/.local/share/tokenmonitor/tokenmon.py" 2>/dev/null; then
  ok "instalação sincronizada com src/"
else
  if [[ $STRICT -eq 1 ]]; then
    bad "instalação desatualizada — rode 'make user-install'"
  else
    warn "instalação desatualizada — rode 'make user-install'"
  fi
fi

echo "== 6/6  janela em execução"
if ! pgrep -f 'python3 .*tokenmon\.py' >/dev/null 2>&1; then
  echo "  · nenhuma instância ativa; iniciando a partir do src/"
  mkdir -p "${TMPDIR:-/tmp}/opencode"
  GDK_BACKEND=x11 nohup python3 src/tokenmon.py \
    >"${TMPDIR:-/tmp}/opencode/smoke-run.log" 2>&1 &
  for _ in $(seq 1 24); do
    sleep 0.5
    wmctrl -l 2>/dev/null | grep -q "Token Monitor" && break
  done
fi

LINE=$(wmctrl -lG 2>/dev/null | grep "Token Monitor" | head -1)
if [[ -n "$LINE" ]]; then
  W=$(awk '{print $5}' <<<"$LINE")
  H=$(awk '{print $6}' <<<"$LINE")
  if [[ "$W $H" == "342 166" || "$W $H" == "138 390" ]]; then
    ok "janela visível e com geometria esperada (${W}×${H})"
  else
    bad "geometria inesperada: ${W}×${H} (esperado 342×166 ou 138×390)"
  fi
else
  bad "janela 'Token Monitor' não encontrada no X11"
fi

echo
echo "resultado: ${PASS} ok · ${WARN} aviso(s) · ${FAIL} falha(s)"
if [[ $FAIL -ne 0 ]]; then
  exit 1
fi
if [[ $STRICT -eq 1 && $WARN -ne 0 ]]; then
  exit 1
fi
exit 0

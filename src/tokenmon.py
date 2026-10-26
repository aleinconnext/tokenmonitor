#!/usr/bin/env python3
"""Token Monitor — medidor visual multi-ferramenta (estilo codenotch).

v2: janela sem moldura, fundo transparente, ancorável nas bordas e
"sempre no topo" (via XWayland + EWMH, porque o GNOME não expõe
always-on-top nem layer-shell para apps GTK4).

Anéis: Claude Code · Cursor · Codex. Hover mostra o detalhamento completo.
Botão direito: ancorar em qualquer borda/canto, alternar topo e sair.
"""
import json
import math
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
import ctypes
import base64

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
import cairo
from gi.repository import Gdk, GLib, Gtk, Pango

APP_ID = "io.github.tokenmonitor.TokenMonitor"
TITLE = "Token Monitor"
CTX_WINDOW = 200_000
STATE_DIR = "~/.config/tokenmonitor"
STATE_FILE = "~/.config/tokenmonitor/state.json"

BG = (0.067, 0.075, 0.094)
TRACK = (0.149, 0.165, 0.200)
TEXT = (0.910, 0.925, 0.953)
SUB = (0.545, 0.576, 0.655)
GREEN = (0.239, 0.863, 0.518)
YELLOW = (1.000, 0.800, 0.302)
RED = (1.000, 0.361, 0.361)

CARD_ALPHA = 0.72
MARGIN = 8
SNAP = 40
HORIZONTAL_SIZE = (342, 166)
VERTICAL_SIZE = (138, 390)
GAUGE_SIZE = 92
GAUGE_GAP = 10

# Glifos monocromáticos (Claude, Cursor, Codex/OpenAI), PNG branco 96x96.
ICONS_B64 = {
    "claude": (
        "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"
    ),
    "cursor": (
        "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"
    ),
    "codex": (
        "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"
    ),
}

CSS = f"""
window, window.background {{ background: transparent; }}
.tokenmon-card {{
  background-color: rgba(17, 19, 24, {CARD_ALPHA});
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  padding: 12px 14px 10px 14px;
}}
.menu-title {{ font-size: 9px; color: #6f7789; padding: 4px 8px 0 8px; }}
.menu-btn {{ font-size: 11px; color: #e8ecf3; }}
.menu-btn:hover {{ background-color: rgba(255,255,255,0.08); }}
"""

ANCHORS = {
    "top-left": (0.0, 0.0),
    "top-center": (0.5, 0.0),
    "top-right": (1.0, 0.0),
    "middle-left": (0.0, 0.5),
    "middle-right": (1.0, 0.5),
    "bottom-left": (0.0, 1.0),
    "bottom-center": (0.5, 1.0),
    "bottom-right": (1.0, 1.0),
}
ANCHOR_LABELS = {
    "top-left": "Topo esquerdo",
    "top-center": "Topo centro",
    "top-right": "Topo direito",
    "middle-left": "Lateral esquerda",
    "middle-right": "Lateral direita",
    "bottom-left": "Base esquerda",
    "bottom-center": "Base centro",
    "bottom-right": "Base direita",
}


# ── utilidades ────────────────────────────────────────────────────────────────
def color_for(pct: float):
    if pct >= 85:
        return RED
    if pct >= 60:
        return YELLOW
    return GREEN


def human(n) -> str:
    n = float(n or 0)
    for unit in ("", "k", "M", "B"):
        if abs(n) < 1000 or unit == "B":
            return f"{int(n)}" if unit == "" else f"{n:.1f}{unit}"
        n /= 1000
    return str(n)


def hhmm(epoch) -> str:
    if not epoch:
        return "—"
    return time.strftime("%d/%m %H:%M", time.localtime(epoch))


def short_reset(epoch) -> str:
    if not epoch:
        return ""
    left = max(0, int(epoch - time.time()))
    h, rem = divmod(left, 3600)
    m, _ = divmod(rem, 60)
    if h >= 48:
        d, hh = divmod(h, 24)
        return f"{d}d {hh}h"
    return f"{h}h{m:02d}" if h else f"{m}min"


def load_state() -> dict:
    try:
        with open(os.path.expanduser(STATE_FILE)) as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return {"anchor": "top-right", "above": True, "monitor": 0}


def save_state(state: dict):
    path = os.path.expanduser(STATE_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w") as fh:
            json.dump(state, fh, indent=2)
    except OSError:
        pass


# ── fonte: Claude Code ────────────────────────────────────────────────────────
def find_monitor():
    for cand in (
        shutil.which("claude-monitor"),
        os.path.expanduser("~/.local/bin/claude-monitor"),
        os.path.expanduser("~/.local/share/uv/tools/claude-monitor/bin/claude-monitor"),
    ):
        if cand and os.path.exists(cand):
            return cand
    return None


def newest_transcript(root, max_age=3600.0):
    if not os.path.isdir(root):
        return None
    best = None
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if best is None or mtime > best[0]:
                best = (mtime, path)
    if best and (time.time() - best[0]) < max_age:
        return best[1]
    return None


def tail_usage(path, chunk=200_000):
    try:
        with open(path, "rb") as fh:
            size = os.path.getsize(path)
            fh.seek(max(0, size - chunk))
            lines = fh.read().splitlines()
    except OSError:
        return None
    for raw in reversed(lines):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        usage = (obj.get("message") or {}).get("usage") or obj.get("usage")
        if usage:
            return usage
    return None


def session_context():
    path = newest_transcript(os.path.expanduser("~/.claude/projects"))
    if not path:
        return None
    usage = tail_usage(path)
    if not usage:
        return None
    used = (
        (usage.get("input_tokens") or 0)
        + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("cache_creation_input_tokens") or 0)
        + (usage.get("output_tokens") or 0)
    )
    return {"used": used, "window": CTX_WINDOW, "pct": min(100.0, used / CTX_WINDOW * 100)}


def collect_claude():
    out = {"id": "claude", "label": "Claude Code", "pct": None, "sub": "—", "detail": [], "note": None}
    mon = find_monitor()
    if not mon:
        out["note"] = "claude-monitor não encontrado"
        return out
    try:
        res = subprocess.run(
            [mon, "--once", "--output", "json"], capture_output=True, text=True, timeout=25
        )
        snap = json.loads(res.stdout)
    except Exception as exc:  # noqa: BLE001
        out["note"] = f"claude-monitor falhou ({exc.__class__.__name__})"
        return out

    five = (snap.get("limits") or {}).get("five_hour") or {}
    week = (snap.get("limits") or {}).get("seven_day") or {}
    local = snap.get("local") or {}
    pace = (snap.get("pace") or {}).get("label")

    pct = five.get("used_percentage")
    out["pct"] = pct
    out["sub"] = short_reset(five.get("resets_at_epoch"))
    out["detail"] = [
        ("Janela 5h", f"{pct:.1f}% · {human(five.get('tokens_used'))}/{human(five.get('token_limit'))} tok"),
        ("Reset 5h", f"{hhmm(five.get('resets_at_epoch'))} ({short_reset(five.get('resets_at_epoch'))})"),
    ]
    if week.get("used_percentage") is not None:
        out["detail"].append(
            ("Janela 7d", f"{week['used_percentage']:.1f}% · reset {hhmm(week.get('resets_at_epoch'))}")
        )
    out["detail"] += [
        ("Sessão", f"{local.get('sent_messages') or 0} mensagens"),
        ("Burn rate", f"{human(local.get('burn_rate_tokens_per_minute'))} tok/min"),
        ("Pace", pace or "—"),
        ("Confiança", five.get("confidence") or "—"),
    ]
    ctx = session_context()
    if ctx:
        out["detail"].append(("Contexto", f"{ctx['pct']:.1f}% · {human(ctx['used'])}/{human(ctx['window'])}"))
    return out


# ── fonte: Cursor ─────────────────────────────────────────────────────────────
CURSOR_DB = "~/.config/Cursor/User/globalStorage/state.vscdb"
_cursor_cache = {"at": 0.0, "data": None}


def cursor_token():
    path = os.path.expanduser(CURSOR_DB)
    if not os.path.exists(path):
        return None, None
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=3)
        rows = dict(
            con.execute(
                "SELECT key, value FROM ItemTable WHERE key IN "
                "('cursorAuth/accessToken','cursorAuth/stripeMembershipType')"
            ).fetchall()
        )
        con.close()
        return rows.get("cursorAuth/accessToken"), rows.get("cursorAuth/stripeMembershipType")
    except Exception:  # noqa: BLE001
        return None, None


def cursor_api(token, path, body=b"{}"):
    req = urllib.request.Request(
        f"https://api2.cursor.sh{path}",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "tokenmonitor/2.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def collect_cursor():
    out = {"id": "cursor", "label": "Cursor", "pct": None, "sub": "—", "detail": [], "note": None}
    token, plan = cursor_token()
    if not token:
        out["note"] = "Cursor não instalado / sem login"
        return out
    if _cursor_cache["data"] and (time.time() - _cursor_cache["at"]) < 60:
        data = _cursor_cache["data"]
    else:
        try:
            data = cursor_api(token, "/aiserver.v1.DashboardService/GetCurrentPeriodUsage")
            _cursor_cache.update(at=time.time(), data=data)
        except Exception as exc:  # noqa: BLE001
            out["note"] = f"API do Cursor indisponível ({exc.__class__.__name__})"
            return out

    usage = data.get("planUsage") or {}
    pct = usage.get("totalPercentUsed")
    start = data.get("billingCycleStart")
    end = data.get("billingCycleEnd")
    start_s = int(start) / 1000 if start else None
    end_s = int(end) / 1000 if end else None

    out["pct"] = pct
    out["sub"] = time.strftime("%d/%m", time.localtime(end_s)) if end_s else "—"
    out["detail"] = [
        ("Plano", (plan or "—").upper()),
        ("Uso incluído", f"{pct:.1f}%" if pct is not None else "—"),
        ("Auto / API", f"{(usage.get('autoPercentUsed') or 0):.1f}% · {(usage.get('apiPercentUsed') or 0):.1f}%"),
        ("Ciclo", f"{hhmm(start_s)} → {hhmm(end_s)}"),
        ("Reset", short_reset(end_s)),
    ]
    for key, label in (
        ("autoModelSelectedDisplayMessage", "Mensagem"),
        ("displayMessage", "Aviso"),
    ):
        if data.get(key):
            out["detail"].append((label, data[key]))
    return out


# ── fonte: Codex ──────────────────────────────────────────────────────────────
CODEX_ROOT = "~/.codex/sessions"


def collect_codex():
    out = {"id": "codex", "label": "Codex", "pct": None, "sub": "—", "detail": [], "note": None}
    path = newest_transcript(os.path.expanduser(CODEX_ROOT), max_age=86400 * 30)
    if not path:
        out["note"] = "sem sessões do Codex nesta máquina"
        return out
    try:
        with open(path, "rb") as fh:
            size = os.path.getsize(path)
            fh.seek(max(0, size - 400_000))
            lines = fh.read().splitlines()
    except OSError:
        out["note"] = "não foi possível ler a sessão"
        return out

    rate = None
    info = None
    for raw in reversed(lines):
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        payload = obj.get("payload") or {}
        if payload.get("rate_limits"):
            rate = payload["rate_limits"]
        if payload.get("info"):
            info = payload["info"]
        if rate is not None:
            break

    if not rate:
        out["note"] = "sessão sem dados de limite"
        return out

    primary = rate.get("primary") or {}
    secondary = rate.get("secondary") or {}
    pct = primary.get("used_percent")
    out["pct"] = pct
    out["sub"] = (
        short_reset(time.time() + primary["resets_in_seconds"]) if primary.get("resets_in_seconds") else "—"
    )
    out["detail"] = [
        ("Janela primária", f"{(primary.get('used_percent') or 0):.1f}% · {primary.get('window_minutes', '?')} min"),
        ("Reset primário", short_reset(time.time() + primary.get("resets_in_seconds", 0))),
    ]
    if secondary:
        out["detail"].append(
            ("Janela secundária",
             f"{(secondary.get('used_percent') or 0):.1f}% · {secondary.get('window_minutes', '?')} min")
        )
    if info:
        total = (info.get("total_token_usage") or {}).get("total_tokens")
        if total:
            out["detail"].append(("Tokens na sessão", human(total)))
        if info.get("model_context_window"):
            out["detail"].append(("Contexto", human(info["model_context_window"])))
    return out


def collect_all():
    results = {}

    def run(fn):
        try:
            results[fn.__name__] = fn()
        except Exception as exc:  # noqa: BLE001
            results[fn.__name__] = {
                "id": fn.__name__, "label": fn.__name__, "pct": None,
                "sub": "—", "detail": [], "note": str(exc),
            }

    threads = [threading.Thread(target=run, args=(fn,)) for fn in (collect_claude, collect_cursor, collect_codex)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return [results[fn] for fn in ("collect_claude", "collect_cursor", "collect_codex") if fn in results]


# ── widgets ───────────────────────────────────────────────────────────────────
class Gauge(Gtk.Overlay):
    def __init__(self, label: str, icon_b64: str | None = None, size: int = GAUGE_SIZE):
        super().__init__()
        self.label = label
        self.size = size
        self.pct = 0.0
        self.extra = ""
        self.muted = True
        self.icon = None

        self.area = Gtk.DrawingArea()
        self.area.set_content_width(size)
        self.area.set_content_height(size + 18)
        self.area.set_draw_func(self._draw)
        self.set_child(self.area)

        if icon_b64:
            try:
                texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(base64.b64decode(icon_b64)))
                self.icon = Gtk.Image.new_from_paintable(texture)
                self.icon.set_pixel_size(32)
                self.icon.set_halign(Gtk.Align.CENTER)
                self.icon.set_valign(Gtk.Align.START)
                self.icon.set_margin_top(int(size / 2) - 19)
                self.icon.set_opacity(0.55)
                self.add_overlay(self.icon)
            except Exception:  # noqa: BLE001
                self.icon = None

    def set_value(self, pct, extra: str = "", muted: bool = False):
        self.pct = max(0.0, min(100.0, float(pct or 0)))
        self.extra = extra
        self.muted = muted
        if self.icon is not None:
            self.icon.set_opacity(0.55 if muted else 1.0)
        self.area.queue_draw()

    def set_details(self, title: str, rows, note: str | None = None):
        esc = GLib.markup_escape_text
        lines = [f"<b>{esc(str(title))}</b>"]
        for key, value in rows:
            lines.append(f"<b>{esc(str(key))}</b>  {esc(str(value))}")
        if note:
            lines.append(f"<i>{esc(str(note))}</i>")
        markup = "\n".join(lines)
        self.set_tooltip_markup(markup)
        self.area.set_tooltip_markup(markup)
        if self.icon is not None:
            self.icon.set_tooltip_markup(markup)

    def _draw(self, _area, ctx, width, height):
        radius = self.size / 2 - 6
        cx, cy = width / 2, radius + 6
        start = math.radians(135)
        sweep = math.radians(270)
        thickness = 8

        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(thickness)
        ctx.set_source_rgb(*TRACK)
        ctx.arc(cx, cy, radius, start, start + sweep)
        ctx.stroke()

        if self.pct > 0:
            ctx.set_source_rgb(*(SUB if self.muted else color_for(self.pct)))
            ctx.arc(cx, cy, radius, start, start + sweep * (self.pct / 100.0))
            ctx.stroke()

        if self.extra:
            ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            ctx.set_source_rgb(*SUB)
            ctx.set_font_size(7.8)
            ext2 = ctx.text_extents(self.extra)
            ctx.move_to(cx - ext2.width / 2 - ext2.x_bearing, cy + 27)
            ctx.show_text(self.extra)

        # Percentual ocupa o lugar do nome do modelo, abaixo do anel.
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_source_rgb(*(SUB if self.muted else color_for(self.pct)))
        text = "—" if self.muted else f"{self.pct:.0f}%"
        ctx.set_font_size(12)
        ext3 = ctx.text_extents(text)
        ctx.move_to(width / 2 - ext3.width / 2 - ext3.x_bearing, height - 4)
        ctx.show_text(text)


# ── X11 (movimento/consulta de ponteiro) ─────────────────────────────────────
class X11:
    """Acesso mínimo a libX11 para mover a janela e ler o ponteiro raiz.

    O arrasto é feito pelo próprio app (sem _NET_WM_MOVERESIZE): assim o
    GTK continua recebendo o botão solto e podemos encaixar nas bordas na
    hora exata em que o usuário solta o mouse.
    """

    def __init__(self):
        self.ok = False
        try:
            lib = ctypes.CDLL("libX11.so.6")
            lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
            lib.XOpenDisplay.restype = ctypes.c_void_p
            lib.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
            lib.XDefaultRootWindow.restype = ctypes.c_ulong
            lib.XMoveWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int]
            lib.XMoveWindow.restype = ctypes.c_int
            lib.XFlush.argtypes = [ctypes.c_void_p]
            lib.XFlush.restype = ctypes.c_int
            lib.XQueryPointer.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.POINTER(ctypes.c_ulong),
                ctypes.POINTER(ctypes.c_ulong),
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_uint),
            ]
            lib.XQueryPointer.restype = ctypes.c_int
            lib.XTranslateCoordinates.argtypes = [
                ctypes.c_void_p,
                ctypes.c_ulong,
                ctypes.c_ulong,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_int),
                ctypes.POINTER(ctypes.c_ulong),
            ]
            lib.XTranslateCoordinates.restype = ctypes.c_int
            display = lib.XOpenDisplay(None)
            if not display:
                return
            self.lib = lib
            self.display = display
            self.root = lib.XDefaultRootWindow(display)
            self.ok = True
        except Exception:  # noqa: BLE001
            self.ok = False

    def pointer(self):
        if not self.ok:
            return None
        root = ctypes.c_ulong()
        child = ctypes.c_ulong()
        rx = ctypes.c_int()
        ry = ctypes.c_int()
        wx = ctypes.c_int()
        wy = ctypes.c_int()
        mask = ctypes.c_uint()
        found = self.lib.XQueryPointer(
            self.display, self.root, ctypes.byref(root), ctypes.byref(child),
            ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(wx), ctypes.byref(wy),
            ctypes.byref(mask),
        )
        if not found:
            return None
        return rx.value, ry.value

    def window_pos(self, xid):
        if not self.ok:
            return None
        rx = ctypes.c_int()
        ry = ctypes.c_int()
        child = ctypes.c_ulong()
        ok = self.lib.XTranslateCoordinates(
            self.display, xid, self.root, 0, 0,
            ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(child),
        )
        if not ok:
            return None
        return rx.value, ry.value

    def move(self, xid, x, y):
        if not self.ok:
            return False
        self.lib.XMoveWindow(self.display, xid, int(x), int(y))
        self.lib.XFlush(self.display)
        return True


# ── janela ────────────────────────────────────────────────────────────────────
class App(Gtk.Application):
    def __init__(self, start_anchor=None):
        super().__init__(application_id=APP_ID, flags=0)
        self.win = None
        self.tools = []
        self.gauges = {}
        self.busy = False
        self.state = load_state()
        self.expected_xy = None
        self.vertical = False
        self.x11 = None
        self.dragging = False
        self.drag_win = None
        self.drag_ptr = None
        self.drag_bounds = None
        self._last_drag_move = 0.0
        if start_anchor:
            self.state["anchor"] = start_anchor

    def do_activate(self):
        if self.win:
            self.win.present()
            return

        self.win = Gtk.ApplicationWindow(application=self, title=TITLE)
        self.win.set_decorated(False)
        self.win.set_resizable(True)
        self.win.set_default_size(*HORIZONTAL_SIZE)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(MARGIN)
        outer.set_margin_bottom(MARGIN)
        outer.set_margin_start(MARGIN)
        outer.set_margin_end(MARGIN)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("tokenmon-card")
        try:
            card.set_cursor(Gdk.Cursor.new_from_name("grab", None))
        except Exception:  # noqa: BLE001
            pass

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=GAUGE_GAP)
        row.set_halign(Gtk.Align.CENTER)
        row.set_valign(Gtk.Align.CENTER)
        for key, label in (("claude", "Claude Code"), ("cursor", "Cursor"), ("codex", "Codex")):
            g = Gauge(label, ICONS_B64.get(key))
            g.set_value(0, "", muted=True)
            self.gauges[key] = g
            row.append(g)
        card.append(row)
        self.row = row

        self.status = Gtk.Label(label="coletando…")
        self.status.set_attributes(self._attrs(size=8))
        self.status.set_margin_top(6)
        card.append(self.status)

        outer.append(card)
        self.outer = outer
        self.card = card
        self.win.set_child(outer)

        self.x11 = X11()
        self._build_menu(card)
        self._install_drag(card)

        self.win.present()
        GLib.timeout_add(400, self._post_map)
        GLib.timeout_add_seconds(20, self._tick)
        GLib.timeout_add_seconds(1, self._track_position)
        self.win.connect("close-request", lambda *_: self.quit())
        self.refresh()

    # ── ancoragem / EWMH ─────────────────────────────────────────────────────
    def _xid(self):
        try:
            from gi.repository import GdkX11

            surface = self.win.get_surface()
            if isinstance(surface, GdkX11.X11Surface):
                return int(GdkX11.X11Surface.get_xid(surface))
        except Exception:  # noqa: BLE001
            pass
        return None

    def _wmctrl(self, *args):
        if not shutil.which("wmctrl"):
            return False
        try:
            subprocess.run(["wmctrl", *args], capture_output=True, timeout=5)
            return True
        except Exception:  # noqa: BLE001
            return False

    def _post_map(self):
        xid = self._xid()
        if not xid:
            self.status.set_text("ancoragem indisponível (backend não-X11)")
            return False
        self._apply_above()
        anchor = self.state.get("anchor", "top-right")
        if anchor == "free" and self.state.get("free_x") is not None:
            self._restore_free()
        else:
            self._apply_anchor(anchor)
        return False

    def _apply_above(self):
        xid = self._xid()
        if not xid:
            return
        action = "add" if self.state.get("above") else "remove"
        self._wmctrl("-i", "-r", hex(xid), "-b", f"{action},above,skip_taskbar")

    def _move_abs(self, x, y, w, h):
        xid = self._xid()
        if not xid:
            return
        self._wmctrl("-i", "-r", hex(xid), "-e", f"0,{int(x)},{int(y)},{int(w)},{int(h)}")
        self.expected_xy = (int(x), int(y))
        GLib.timeout_add(300, self._move_abs_retry, int(x), int(y), int(w), int(h))

    def _move_abs_retry(self, x, y, w, h):
        # Reaplica uma vez: evita corrida entre a troca de orientação/tamanho
        # e a primeira aplicação feita pelo gerenciador de janelas.
        xid = self._xid()
        if xid:
            self._wmctrl("-i", "-r", hex(xid), "-e", f"0,{x},{y},{w},{h}")
        return False

    def _window_pos(self):
        xid = self._xid()
        if not xid:
            return None
        if self.x11 and self.x11.ok:
            pos = self.x11.window_pos(xid)
            if pos:
                return pos
        try:
            out = subprocess.run(
                ["xwininfo", "-id", hex(xid)], capture_output=True, text=True, timeout=3
            ).stdout
        except Exception:  # noqa: BLE001
            return None
        x = y = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Absolute upper-left X:"):
                x = int(line.split(":", 1)[1])
            elif line.startswith("Absolute upper-left Y:"):
                y = int(line.split(":", 1)[1])
        if x is None or y is None:
            return None
        return x, y

    def _move_now(self, x, y):
        xid = self._xid()
        if not xid:
            return
        if not (self.x11 and self.x11.move(xid, x, y)):
            win_w = self.win.get_width() or HORIZONTAL_SIZE[0]
            win_h = self.win.get_height() or HORIZONTAL_SIZE[1]
            self._wmctrl("-i", "-r", hex(xid), "-e", f"0,{int(x)},{int(y)},{win_w},{win_h}")
        self.expected_xy = (int(x), int(y))

    def _screen_bounds(self):
        monitors = Gdk.Display.get_default().get_monitors()
        if not monitors:
            return None
        minx = miny = 10**9
        maxx = maxy = -10**9
        for index in range(monitors.get_n_items()):
            geo = monitors.get_item(index).get_geometry()
            minx = min(minx, geo.x)
            miny = min(miny, geo.y)
            maxx = max(maxx, geo.x + geo.width)
            maxy = max(maxy, geo.y + geo.height)
        return minx, miny, maxx, maxy

    # ── arrasto próprio + encaixe nas bordas ─────────────────────────────────
    def _install_drag(self, widget):
        gesture = Gtk.GestureDrag()
        gesture.set_button(1)
        gesture.connect("drag-begin", self._drag_begin)
        gesture.connect("drag-update", self._drag_update)
        gesture.connect("drag-end", self._drag_end)
        widget.add_controller(gesture)

    def _drag_begin(self, *_args):
        if not (self.x11 and self.x11.ok):
            return
        pos = self._window_pos()
        ptr = self.x11.pointer()
        if not pos or not ptr:
            return
        self.dragging = True
        self.drag_win = pos
        self.drag_ptr = ptr
        self.drag_bounds = self._screen_bounds()
        self._last_drag_move = 0.0
        self._set_cursor("grabbing")

    def _drag_update(self, *_args):
        if not self.dragging or not (self.x11 and self.x11.ok):
            return
        now = time.monotonic()
        if now - self._last_drag_move < 0.012:
            return
        ptr = self.x11.pointer()
        if not ptr:
            return
        self._last_drag_move = now
        x = self.drag_win[0] + (ptr[0] - self.drag_ptr[0])
        y = self.drag_win[1] + (ptr[1] - self.drag_ptr[1])
        if self.drag_bounds:
            minx, miny, maxx, maxy = self.drag_bounds
            win_w = self.win.get_width()
            win_h = self.win.get_height()
            x = max(minx, min(x, maxx - win_w))
            y = max(miny, min(y, maxy - win_h))
        self._move_now(x, y)

    def _drag_end(self, *_args):
        if not self.dragging:
            return
        self.dragging = False
        self._set_cursor("grab")
        # Espera o WM aplicar o último movimento (e possíveis clamps) antes
        # de decidir em qual borda a janela foi solta.
        GLib.timeout_add(130, self._snap_now)

    def _snap_now(self):
        self._snap()
        return False

    def _set_cursor(self, name):
        try:
            self.card.set_cursor(Gdk.Cursor.new_from_name(name, None))
        except Exception:  # noqa: BLE001
            pass

    def _snap(self):
        """Encaixa na borda mais próxima; laterais trocam para vertical."""
        # Usa a posição real; se o WM ainda não aplicou nada, cai para a
        # última posição solicitada.
        pos = self._window_pos() or self.expected_xy
        if not pos:
            return
        x, y = pos
        win_w = self.win.get_width()
        win_h = self.win.get_height()
        geo = self._workarea_at(x + win_w // 2, y + win_h // 2)
        if not geo:
            return

        left = abs(x - geo.x) <= SNAP
        right = abs((geo.x + geo.width) - (x + win_w)) <= SNAP
        top = abs(y - geo.y) <= SNAP
        bottom = abs((geo.y + geo.height) - (y + win_h)) <= SNAP

        if left or right:
            win_w, win_h = self._set_orientation(True)
            nx = geo.x + MARGIN if left else geo.x + geo.width - win_w - MARGIN
            ny = max(geo.y + MARGIN, min(y, geo.y + geo.height - win_h - MARGIN))
            self._move_abs(nx, ny, win_w, win_h)
            self.state.update(anchor="free", free_x=nx, free_y=ny, vertical=True)
        elif top or bottom:
            win_w, win_h = self._set_orientation(False)
            nx = max(geo.x + MARGIN, min(x, geo.x + geo.width - win_w - MARGIN))
            ny = geo.y + MARGIN if top else geo.y + geo.height - win_h - MARGIN
            self._move_abs(nx, ny, win_w, win_h)
            self.state.update(anchor="free", free_x=nx, free_y=ny, vertical=False)
        else:
            self.expected_xy = (x, y)
            self.state.update(anchor="free", free_x=x, free_y=y, vertical=self.vertical)
        save_state(self.state)

    def _set_orientation(self, vertical: bool):
        self.vertical = bool(vertical)
        if vertical:
            self.row.set_orientation(Gtk.Orientation.VERTICAL)
            self.status.set_visible(False)
            size = VERTICAL_SIZE
        else:
            self.row.set_orientation(Gtk.Orientation.HORIZONTAL)
            self.status.set_visible(True)
            size = HORIZONTAL_SIZE
        self.row.set_halign(Gtk.Align.CENTER)
        self.row.set_valign(Gtk.Align.CENTER)
        self.win.set_default_size(*size)
        self.state["vertical"] = self.vertical
        return size

    def _workarea_at(self, x, y):
        display = Gdk.Display.get_default()
        monitors = display.get_monitors()
        if monitors:
            for index in range(monitors.get_n_items()):
                geo = monitors.get_item(index).get_workarea()
                if geo.x <= x < geo.x + geo.width and geo.y <= y < geo.y + geo.height:
                    return geo
        return self._workarea()

    def _restore_free(self):
        geo = self._workarea_at(int(self.state.get("free_x", 0)), int(self.state.get("free_y", 0)))
        vertical = bool(self.state.get("vertical", False))
        win_w, win_h = self._set_orientation(vertical)
        x = int(self.state.get("free_x", 0))
        y = int(self.state.get("free_y", 0))
        if geo:
            x = max(geo.x, min(x, geo.x + geo.width - win_w))
            y = max(geo.y, min(y, geo.y + geo.height - win_h))
        self._move_abs(x, y, win_w, win_h)

    def _track_position(self):
        if self.dragging:
            return True
        xid = self._xid()
        if not xid:
            return True
        try:
            out = subprocess.run(
                ["xwininfo", "-id", hex(xid)], capture_output=True, text=True, timeout=3
            ).stdout
        except Exception:  # noqa: BLE001
            return True
        x = y = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Absolute upper-left X:"):
                x = int(line.split(":", 1)[1])
            elif line.startswith("Absolute upper-left Y:"):
                y = int(line.split(":", 1)[1])
        if x is None or y is None:
            return True
        if self.expected_xy is None:
            self.expected_xy = (x, y)
            return True
        ex, ey = self.expected_xy
        if abs(x - ex) > 2 or abs(y - ey) > 2:
            self.state.update(anchor="free", free_x=x, free_y=y, vertical=self.vertical)
            save_state(self.state)
            self.expected_xy = (x, y)
        return True

    def _workarea(self):
        display = Gdk.Display.get_default()
        monitors = display.get_monitors()
        total = monitors.get_n_items()
        if not total:
            return None
        index = self.state.get("monitor", 0)
        if not isinstance(index, int) or index < 0 or index >= total:
            index = 0
        mon = monitors.get_item(index)
        return mon.get_workarea() if mon else None

    def _monitor_count(self):
        monitors = Gdk.Display.get_default().get_monitors()
        return monitors.get_n_items() if monitors else 0

    def _cycle_monitor(self):
        total = self._monitor_count()
        if total < 2:
            return
        self.menu.popdown()
        self.state["monitor"] = (self.state.get("monitor", 0) + 1) % total
        save_state(self.state)
        anchor = self.state.get("anchor", "top-right")
        if anchor not in ANCHORS:
            anchor = "top-right"
        self._apply_anchor(anchor)

    def _apply_anchor(self, name: str):
        if name not in ANCHORS:
            return
        geo = self._workarea()
        xid = self._xid()
        if not geo or not xid:
            return
        win_w, win_h = self._set_orientation(name in ("middle-left", "middle-right"))
        fx, fy = ANCHORS[name]
        x = geo.x + MARGIN + int((geo.width - win_w - 2 * MARGIN) * fx)
        y = geo.y + MARGIN + int((geo.height - win_h - 2 * MARGIN) * fy)
        self._move_abs(x, y, win_w, win_h)
        self.state["anchor"] = name
        save_state(self.state)

    # ── menu / interação ─────────────────────────────────────────────────────
    def _build_menu(self, parent):
        self.menu = Gtk.Popover()
        self.menu.set_parent(parent)
        self.menu.set_has_arrow(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(4)
        box.set_margin_end(4)

        title = Gtk.Label(label="ANCORAR")
        title.set_xalign(0)
        title.add_css_class("menu-title")
        box.append(title)

        for name, label in ANCHOR_LABELS.items():
            btn = Gtk.Button(label=label)
            btn.add_css_class("flat")
            btn.add_css_class("menu-btn")
            btn.connect("clicked", lambda _b, n=name: self._anchor_from_menu(n))
            box.append(btn)

        box.append(Gtk.Separator())

        if self._monitor_count() > 1:
            btn_screen = Gtk.Button(label="Trocar de tela")
            btn_screen.add_css_class("flat")
            btn_screen.add_css_class("menu-btn")
            btn_screen.connect("clicked", lambda *_: self._cycle_monitor())
            box.append(btn_screen)
            box.append(Gtk.Separator())

        self.btn_above = Gtk.Button()
        self.btn_above.add_css_class("flat")
        self.btn_above.add_css_class("menu-btn")
        self.btn_above.connect("clicked", lambda *_: self._toggle_above())
        box.append(self.btn_above)
        self._sync_above_label()

        for label, cb in (
            ("Abrir painel do FreeLLMAPI", self.open_dashboard),
            ("Abrir monitor TUI", self.open_tui),
            ("Sair", lambda *_: self.quit()),
        ):
            b = Gtk.Button(label=label)
            b.add_css_class("flat")
            b.add_css_class("menu-btn")
            b.connect("clicked", cb)
            box.append(b)

        self.menu.set_child(box)

        click = Gtk.GestureClick()
        click.set_button(3)
        click.connect("pressed", self._on_right_click)
        parent.add_controller(click)

    def _on_right_click(self, gesture, _n, x, y):
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self.menu.set_pointing_to(rect)
        self.menu.popup()

    def _anchor_from_menu(self, name):
        self.menu.popdown()
        self._apply_anchor(name)

    def _toggle_above(self):
        self.state["above"] = not self.state.get("above", True)
        save_state(self.state)
        self._apply_above()
        self._sync_above_label()

    def _sync_above_label(self):
        on = self.state.get("above", True)
        self.btn_above.set_label(f"Sempre no topo: {'ligado' if on else 'desligado'}")

    @staticmethod
    def _attrs(size=10, weight=Pango.Weight.NORMAL):
        a = Pango.AttrList()
        a.insert(Pango.attr_size_new_absolute(int(size * Pango.SCALE)))
        a.insert(Pango.attr_weight_new(weight))
        return a

    # ── ações ────────────────────────────────────────────────────────────────
    def open_dashboard(self, *_):
        subprocess.Popen(["xdg-open", "http://localhost:3001"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def open_tui(self, *_):
        exe = shutil.which("gnome-terminal")
        mon = os.path.expanduser("~/.local/bin/claude-monitor")
        if exe and os.path.exists(mon):
            subprocess.Popen([exe, "--window", "--", mon, "--theme", "dark"])

    def _tick(self):
        self.refresh()
        return True

    def refresh(self):
        if self.busy:
            return
        self.busy = True
        self.status.set_text("coletando…")

        def work():
            GLib.idle_add(self._apply, collect_all())

        threading.Thread(target=work, daemon=True).start()

    def _apply(self, tools):
        self.busy = False
        self.tools = tools
        parts = []
        for tool in tools:
            g = self.gauges.get(tool.get("id"))
            if not g:
                continue
            has = tool.get("pct") is not None
            g.set_value(tool.get("pct") or 0, tool.get("sub") or "", muted=not has)
            g.set_details(
                tool.get("label", "?"),
                tool.get("detail") or [("Status", "sem dados")],
                tool.get("note"),
            )
            parts.append(f"{tool.get('label')} " + ("—" if not has else f"{tool['pct']:.0f}%"))
        self.status.set_text("  ·  ".join(parts))
        return False


def main():
    anchor = None
    if "--anchor" in sys.argv:
        idx = sys.argv.index("--anchor")
        if idx + 1 < len(sys.argv):
            anchor = sys.argv[idx + 1]
    if len(sys.argv) > 2 and sys.argv[1] == "--png":
        return 0
    return App(start_anchor=anchor).run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(main())

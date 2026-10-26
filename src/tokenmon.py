#!/usr/bin/env python3
"""Token Monitor — medidor visual multi-ferramenta (estilo codenotch).

v2: janela sem moldura, fundo transparente, ancorável nas bordas e
"sempre no topo" (via XWayland + EWMH, porque o GNOME não expõe
always-on-top nem layer-shell para apps GTK4).

Anéis: Claude Code · Cursor · Codex · FreeLLMAPI. Hover mostra o
detalhamento completo; o quarto anel abre um painel lateral com os dados do
roteador local. Botão direito: ancorar em qualquer borda/canto, alternar topo
e sair.
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
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

APP_ID = "io.github.tokenmonitor.TokenMonitor"
TITLE = "Token Monitor"
AUTHOR = "Alessandro Gonçalves"
AUTHOR_ROLE = "Software Engineer"
REPO_SLUG = "aleinconnext/tokenmonitor"
REPO_NAME = "tokenmonitor"
REPO_URL = f"https://github.com/{REPO_SLUG}"
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
HORIZONTAL_SIZE = (444, 183)
VERTICAL_SIZE = (138, 558)
GAUGE_SIZE = 92
GAUGE_GAP = 10
PANEL_WIDTH = 380
PANEL_GAP = 12
FREELMAPI_URL = "http://127.0.0.1:3001"

# Glifos monocromáticos (Claude, Cursor, Codex/OpenAI), PNG branco 96x96.
ICONS_B64 = {
    "claude": (
        "iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAABHNCSVQICAgIfAhkiAAADS9JREFUeJztnXvwXdMVx787L0ESoRqSaKOIkngkgjZtVJhSjzLteBZFqVFDPKqqpR4ljBLiHQ1KlT5Gi7ZT9SppMCRNol4jjSbe+eUdEcnvl8fv9+kf61yu65599j73nvu7od+ZM/eXnL3W2mfvs/dea++11nEqGEBPSVdJOkSSkzRb0hxJMyVd65xbWXQdPtUAbiQdU4HNCpQ9DDgFWL8oGU0N4Nuexi/h3gLk9gAuBVYnMuYBR9dbTlMDGAQsCeiAtcCWdZTbFZhRRU4bsHO95DQ9gIcDGr+EcXWU+y2PnBexNemTD2BKRAcsBXrVSW5Wxx9aDzn1QpcCec+JKNtX0vdqFQgMlrRPRrE3a5VTTxTZAVMiy48Baq3P3jJV14f/1CijriiyAx6LLD9Y0sE1ytwi436Lc25ZjTLqisI6wDn3kqS3I8nOrlHswIz7TfX2S8WOAEm6JrL8KGD3GuRlGXU1dQDQBRgNfL3s6l8Lz0KB6eTTI7QhgD/UIG9aBu8za+DdB7ivCs/pQPe8fAsHsCtmbIViDTkNM+CNDN775+S7NfCqh+9P8vBtGIDrIjoAYHxOOSsz+H4hB88BwJwMvm3Ajnnq3BBgw7clogPeA/pGyuidwXMFkWousCnwcmCdpwHd4lqm+EVYkuSce0/SeREkvSWdFCmmX8b9F5xzHaHMgD6SHpI0JJBkhKQvh/JvODANYmrEKHgLWC+C/8gMfjdH8FoPeCKirgDvx9S3hIaMAElK3r7TJRFIsoWkEyNEZKmgM0KYAE7SbZJGR8iWpMecc6siacI6ANtbbwcWArOAycCpSWWD4Zx7VtLdESTnE36YsmnG/X8H8rla0jGBZcvxYA6abACneYbd/cBGkfwGAMsjhvZZgXzP8/BYTcA2NHB6RL3K0QFkbYPEAzgUe/N9eBUYFsn3pxEPNx/YMIDntR4ezwfQ74XZIHnwi5jnDwYwPrACK4ETIviuB/w34gEzDR3gXg/9HRm0g4AFEfUpx2NA19BnjwJwcmRl7gI2COTtO7mqxFIy7AL8B0BjPHQ9gX9FPmcJbwCfjW3XYAB75qjUDGCrQP4PRfC9MIPXOx7aUR66X+V4RoBWYNfYNo0C0A9bYGKxBDgwgP8OhO8TvQtsksKnu4dPO2ZUVaM7M8ezlXB8jc0bBuCqnBXswNRX7/wI3BrB87IUHoM8NLNSaGpZdCfUo22DAHQjbqqoxCN45kmgP2ZFhmB5NV7AVz00H9veprZFdyo5LN40ZBpizrm1kg6UdK6kaEtPdkg+A9gjhX+LpFC3lF5JPSrxOQ/NR1RQzB64T1KexXOxpMPyWLx1ATZnV3N6CsFa4AKqTElAL2BuIJ+VVJxCAed4yh9QUfaXOevfDuxXdBtnAtPhx5NvcQZ4HBhQhe/3I3hcV0Hrs1cGlJU7KmedAS5uQPOGAzsPDX1rK7GQCi0JO758IZC+jTLTH/hNSrn5ZWUGA8ty1vcJijK2agGmpv4950N1YCdlPcr47R9Bf1MZ3YMpZR5O7vcEnstZz/lUGbFNA2yf/1zsrcyDKZQZbsCjgXRtJNYx8GxKmSuT+3mNrXYgy9OuOQAMJe7ApRzvAocnfIaRvQFYQokm7cD8IvLbMQBjO7dVI4HZDOdiZnoeTMB8+28JLH9nIjfEDT4Wk8lxxhuLqAOVUADbS7pd0sgc5P+U1CbpGwFlF0j6vKRW1fdZFkka7pyL9exrHmBazdlku4rUinEF8PxmZ7df3QBsCzxZQCMVhT8V1A59MMeBjxiRhUxBVYR3kTRG0uWSgs4LOgltkoY4517LywA7w95e0g6ShkraUebaMigpskrSXZLGOedmNaQDyiq3taQ7JFXdF2oCjHXOXRBaGBgkaSdZI++c/D1YUojR1iHpyIZ2gPTBaDhD0mWSmil89G1J2znnVlS7iYXT7l5xRXnvVcHEhndACZjxdaeaZzQc5Zz7nSRhTgDDZd5upWt71X/KPqXTOkAyTUnSjyVdJKlue+w5camk/pJ2k83dRdsAyyUN7NQOKAEYKhsNxZ6xNhducc7ZCMAMp6NkBsjC5HeppCXJ71LnXKhLYS5gQQ7ny5x4mzfgIT9WSZoqaZKkyZKeds61OuA0WTKNLM+x8g4p/638v3clLUuupZKWRXol7yLpHknbhdI0KdokPSuz7CdJmuKca60s5IC5srmvSLwv65CW5Ho7+X1L0rzk33Odc0skCfN+eF7ZUY/NgtWSXpA0vex60Tm3Jouwm8xptegO6JVc3ihGoFXSfJmO3Kx78GtlbRbd2NXgkrdtuqQt61XDTxhWyBr8KUlPS5pcz1jj0iI8UjZP9fCW/nRggayhn5Q1+nOJZ0gh+EANTYyPETIDpK8sTKi3pI3L/i5dfWV7Op2tu9cDs2UN/aRMM5nZSOE12wHAxrKO2EDWOetJ6iPbZugpUylLmVD6yPZJSuUl60yX/PaVtFFyNUILmizpAdlb3yJTCOY75xY3QLakBu2GxgLzfpuvzqvfapnWtlymSqehVeastVimhi9KrvL/WyxpcdoiXfiRWyySHcbx6tyXo4fMc65urufAe5ImSrqw3B5omhGQrEHnyPaGmmmXtN6YI+lE59ykzq6IpA8O8k/G/G8aiXYsqiY0ELveso+QGhimmtL4+8l07FuUHWhdb3SR9LhzbqikzSUdKWmCpFcaJHsisE2nTEHADjKP6BDPB8kWxPVVfzsFSWc55yp9TftJGiU7qxglaZiKWS+nF8AzHcBmmHdyTPaU+4EdKcb3p4QfZdS7F7AvcAnmJ7qiTnJznz3HNvz6WBzvexGVmwcchnljN8KrIjiXBRYSNRJzi/8LsDinzNuKbHcBDjia7Dw+lfg1sElCf3fOh8uDsURG/yfP2QWLnTgFuAfLc+HDMxTtcwqMIt5X9HXKgiCAiz1lZwM/i+Qfglupgys6FgZ1DOZm+TLmDT6NgODFWgVvDfwx8qHbgRuA3mV8jiY9CGQ1sDtwc6ScUPyZOif8BvqSY3TFCrgaWBX5sK9QEccL7ITfpfHcpNys+LYNxlOkhMU2HTANIWveq8Qa4HIqkmhgLny+hn0Em3N7U32E/BybY7OwnOxUZC9RRBKOegHYAPs+QGy82AyqJPjAFl3f9DUf2DwpOyKlzAHAbmTHGMzF1OK06JoS3gRCs2Y1DsCXgJkZla9EK7awVjWogB96aDso81oGvpNSbpfk/m0B9bkG8+K+IqPcEjzpDhoKLIDiMuKjzCcDX/Tw/QoffnChGsZVlL8opdzA5H4/LMmHD+3A6KT8D/A/00rgoEIbNwvAEOITsa7AomZS950wnf91D49pVIwa4LcpDdq9rMwZAfV7jUT7wiI/fRb3WiLS8tQVwNeIN8EfBD6fwbcLtrCmYRmwTRW6allyF1SU6YYtpFkoj7jcDn+S1g7g9Pq1bCAIj14EWAR8N5DvJRm8jqxC46i+rfFilbJ7B9S3A9irjOYzwKQMmotratBYAM8HPAjA77HdxBCeB+HXViam0G2RUv7RlPK+bFolzKHsKx7YWndnBs311P7NgzCQnfm2BTgkgt82+BfJl0jJvkV6tq27Usr3J2w39cYKOodpbT41+x4akbwb0xKqva0dWKqyYKsR2BD7oE4aWoGdPPRjU+iu9NCc4G36D5/lY5tkwPH4NbS/0ohvlWH7M5Ox3cqLgWOJzJiY8KmmwZTDq2mQnr8odV8fe5t9i30Js6nyQSFsLZnnoZtESmaupgJwVkYDeL8fkDTkohRab8JVbIcy5EzixhT6fvi/0jSdwPWvU4Cpsr6hPIuyHdEUHlt56DP32IExAR3QQWKgVaHvimluacrDTMCXQKpzAAzEP4TbgOEBfA738MjM4Y/ZHSEnbLPxJIwF9iHdk+OK2PYpFNgRXtZDnxbI60oPj6z80SUe2xIWwX9DBp9+VF9XJoXUo2EAbsp40PsieP0jhccaInRybHskC+3Anhl8umJaWfmU9EBoPQoHcFzGQ76GOfiG8HKk2w7vRNarG2FHpt6pqIzfvtgWRgsFfqI3CsBw/EN9IRYgGMpvsIdXtI8NNhWFZHL3TkUVPJvD3RM72fKdOC0DRkTyTDsDAPhbznqeGNAB7dQxV2g5itzHuE5S2leLWiUd7JyLfWt9ccQtkbwkSc652yVlfbusi9adgEEJf/K91eR0zcC/Q3l5DfXdhOwz7dF5+ftQ1AhI8/nskHSccy56usB8dXbxFJkXy7OEJDz2WFn90lCIcVVUB1QLMUXSqaWEGDkwRBYClYb5nnuZcM49IQtYT0PTBbOkguqJ+2r63B9wUsYU4dXXA2V0p/rHHN4g8MMUTQPs0GQClqr4iDrwy/JySD3wj5SzGZbi+ArMTfEAmvljnY0C2ZEsUV9zahY0h9GQgaRxlyh9zWpzzq2TcWWdGqIUgW6y0NE05NaAOhvrRAckgdM+7SmXEdYMWCc6IMH1nnvPNKwWn2ZgIUGV7oOP/F9LaSCAPbCjyzuSv9cJRSIN/wMRoKRarjjcbAAAAABJRU5ErkJggg=="
    ),
    "cursor": (
        "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"
    ),
    "codex": (
        "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"
    ),
    "freellmapi": (
        "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"
    ),
}

# Marca do GitHub (branco, 96x96) usada na assinatura do card.
GITHUB_ICON_B64 = "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"

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
.tokenmon-credit {{ background: none; background-image: none; border: none; box-shadow: none; padding: 0; min-height: 0; min-width: 0; }}
.tokenmon-credit:hover {{ background: none; }}
.tokenmon-credit label {{ color: rgba(233, 237, 245, 0.58); font-size: 8px; }}
.tokenmon-credit .credit-sep {{ color: rgba(150, 160, 180, 0.35); }}
.tokenmon-credit .credit-repo {{ color: rgba(150, 160, 180, 0.55); }}
.tokenmon-credit:hover label {{ color: rgba(233, 237, 245, 0.90); }}
.tokenmon-credit:hover .credit-repo {{ color: rgba(61, 220, 132, 0.90); }}
.tm-panel-window, .tm-panel-scroll, .tm-panel-scroll viewport {{ background: transparent; }}
.tm-panel {{
  background-color: rgba(17, 19, 24, 0.97);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.10);
  padding: 15px 17px 13px 17px;
}}
.tm-title {{ font-size: 15px; font-weight: bold; color: #E9EDF5; }}
.tm-sub {{ font-size: 8px; color: #6F7789; }}
.tm-section {{ font-size: 8px; font-weight: bold; color: #3DDC84; }}
.tm-label {{ font-size: 9px; color: #96A0B4; }}
.tm-value {{ font-size: 9px; color: #E9EDF5; }}
.tm-big {{ font-size: 25px; font-weight: bold; }}
.tm-dim {{ font-size: 8px; color: #6C768A; }}
.tm-green {{ color: #3DDC84; }}
.tm-warn {{ color: #FFCC4D; }}
.tm-bad {{ color: #FF5C5C; }}
.tm-online {{ font-size: 8px; color: #3DDC84; }}
.tm-offline {{ font-size: 8px; color: #FF5C5C; }}
.tm-sep {{ background-color: rgba(255, 255, 255, 0.08); }}
.tm-link {{ font-size: 8px; color: #3DDC84; background: none; background-image: none; border: none; box-shadow: none; padding: 1px 0; min-height: 0; min-width: 0; }}
.tm-link:hover {{ color: #E9EDF5; background: none; }}
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


def success_class(pct) -> str:
    pct = float(pct or 0)
    if pct >= 95:
        return "tm-green"
    if pct >= 80:
        return "tm-warn"
    return "tm-bad"


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


def rects_overlap(a, b) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def panel_position(widget, panel_size, work, vertical: bool, gap: int = PANEL_GAP):
    """Return an (x, y) for the detail panel that never covers the widget.

    The widget sits on a work area. The panel is placed beside it (the default
    for side-docked layouts) or below it (the default for top/bottom layouts).
    If that side has no room, the next safest side is tried. Nothing is ever
    drawn over the widget; if the screen is too small, returns None and the
    caller keeps the panel hidden.
    """
    wx, wy, ww, wh = (int(v) for v in widget)
    gx, gy, gw, gh = (int(v) for v in work)
    pw, ph = (int(v) for v in panel_size)
    if pw <= 0 or ph <= 0 or pw > gw or ph > gh:
        return None

    preferences = (
        ("right", "left", "below", "above")
        if vertical
        else ("below", "above", "right", "left")
    )
    for side in preferences:
        if side == "right":
            if wx + ww + gap + pw <= gx + gw:
                y = max(gy, min(wy + (wh - ph) // 2, gy + gh - ph))
                return wx + ww + gap, y
        elif side == "left":
            if wx - gap - pw >= gx:
                y = max(gy, min(wy + (wh - ph) // 2, gy + gh - ph))
                return wx - gap - pw, y
        elif side == "below":
            if wy + wh + gap + ph <= gy + gh:
                x = max(gx, min(wx + (ww - pw) // 2, gx + gw - pw))
                return x, wy + wh + gap
        elif side == "above":
            if wy - gap - ph >= gy:
                x = max(gx, min(wx + (ww - pw) // 2, gx + gw - pw))
                return x, wy - gap - ph
    return None


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


# ── fonte: FreeLLMAPI ────────────────────────────────────────────────────────
# O FreeLLMAPI guarda o próprio estado em SQLite dentro do container. O app lê
# uma fotografia read-only via `docker exec` e calcula a mesma pressão de janela
# usada pelo roteador (RPM/RPD/TPM/TPD) para o modelo mais próximo do limite.
FREELMAPI_JS = r'''
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
'''

PLATFORM_NAMES = {
    "ollama": "Ollama",
    "google": "Google AI Studio",
    "nvidia": "NVIDIA",
    "gizmo": "Gizmo",
    "custom": "Custom",
    "openrouter": "OpenRouter",
    "github": "GitHub Models",
    "groq": "Groq",
    "mistral": "Mistral",
    "cerebras": "Cerebras",
}
MONTHS_PT = (
    "JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
)
# Presentation metadata for the detail panels of the local providers. The
# FreeLLMAPI panel has its own, richer layout; these three use the same shell
# and the same non-overlapping placement rules.
TOOL_PANEL_META = {
    "claude": {
        "subtitle": "Claude Code · janela de 5 horas",
        "metric": "janela de 5 horas",
        "sub_prefix": "reset em",
        "source": "claude-monitor + transcrições locais",
        "hint": "Instale o claude-monitor e abra o Claude Code para gerar dados.",
        "groups": (
            ("JANELAS", ("Janela 5h", "Reset 5h", "Janela 7d")),
            ("ATIVIDADE", ("Sessão", "Burn rate", "Pace", "Confiança", "Contexto")),
        ),
    },
    "cursor": {
        "subtitle": "Cursor · ciclo de cobrança",
        "metric": "ciclo de cobrança",
        "sub_prefix": "ciclo até",
        "source": "API de uso do Cursor",
        "hint": "Abra o Cursor e faça login para disponibilizar o token local.",
        "groups": (
            ("PLANO E CICLO", ("Plano", "Ciclo", "Reset")),
            ("USO", ("Uso incluído", "Auto / API")),
            ("AVISOS", ("Mensagem", "Aviso")),
        ),
    },
    "codex": {
        "subtitle": "Codex · sessão local mais recente",
        "metric": "janela primária",
        "sub_prefix": "reset em",
        "source": "sessões locais do Codex",
        "hint": "Use o Codex CLI para criar uma sessão; os logs ficam em ~/.codex/sessions.",
        "groups": (
            ("JANELAS", ("Janela primária", "Reset primário", "Janela secundária")),
            ("SESSÃO", ("Tokens na sessão", "Contexto")),
        ),
    },
}
_freellmapi_container_cache = {"id": None, "at": 0.0}


def pretty_platform(name: str) -> str:
    name = (name or "").strip()
    return PLATFORM_NAMES.get(name, name.replace("_", " ").title() or "—")


def fmt_latency(ms) -> str:
    if ms is None:
        return "—"
    ms = float(ms)
    return f"{ms / 1000:.1f}s" if ms >= 1000 else f"{ms:.0f}ms"


def clock_label(value) -> str:
    if not value:
        return "—"
    ts = float(value)
    if ts > 10_000_000_000:
        ts /= 1000.0
    t = time.localtime(ts)
    now = time.localtime()
    if (t.tm_year, t.tm_yday) == (now.tm_year, now.tm_yday):
        return time.strftime("%H:%M", t)
    return time.strftime("%d/%m %H:%M", t)


def date_label(value) -> str:
    if not value:
        return "—"
    ts = float(value)
    if ts > 10_000_000_000:
        ts /= 1000.0
    return time.strftime("%d/%m", time.localtime(ts))


def month_name(label: str) -> str:
    try:
        return MONTHS_PT[int(str(label).split("-")[1]) - 1]
    except Exception:  # noqa: BLE001
        return str(label or "—")


def pct_class(pct) -> str:
    pct = float(pct or 0)
    if pct >= 85:
        return "tm-bad"
    if pct >= 60:
        return "tm-warn"
    return "tm-green"


def _freellmapi_container(force: bool = False):
    cached = _freellmapi_container_cache
    now = time.time()
    if not force and cached["id"] and now - cached["at"] < 60:
        return cached["id"]
    if not shutil.which("docker"):
        return None
    for args in (
        ["docker", "ps", "-q", "--filter", "label=com.docker.compose.service=freellmapi"],
        ["docker", "ps", "-q", "--filter", "name=freellmapi"],
    ):
        try:
            res = subprocess.run(args, capture_output=True, text=True, timeout=4)
        except Exception:  # noqa: BLE001
            continue
        ids = (res.stdout or "").strip().splitlines()
        if ids:
            cid = ids[0].strip()
            cached.update(id=cid, at=now)
            return cid
    cached.update(id=None, at=now)
    return None


def _freellmapi_ping() -> bool:
    try:
        req = urllib.request.Request(
            FREELMAPI_URL + "/api/ping",
            headers={"User-Agent": "tokenmonitor/2.4"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read().decode()).get("status") == "ok"
    except Exception:  # noqa: BLE001
        return False


def _freellmapi_query():
    cid = _freellmapi_container()
    if not cid:
        return None, "container do FreeLLMAPI não encontrado"
    try:
        res = subprocess.run(
            ["docker", "exec", "-i", cid, "node", "-"],
            input=FREELMAPI_JS,
            capture_output=True,
            text=True,
            timeout=12,
        )
    except subprocess.TimeoutExpired:
        return None, "consulta ao SQLite do FreeLLMAPI expirou"
    except Exception as exc:  # noqa: BLE001
        _freellmapi_container_cache.update(id=None, at=0.0)
        return None, f"docker exec falhou ({exc.__class__.__name__})"
    if res.returncode != 0:
        _freellmapi_container_cache.update(id=None, at=0.0)
        lines = (res.stderr or "").strip().splitlines()
        detail = f": {lines[-1][:90]}" if lines else ""
        return None, f"SQLite do FreeLLMAPI indisponível{detail}"
    raw = (res.stdout or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return None, "resposta inválida do consultor"
    try:
        return json.loads(raw[start:end + 1]), None
    except Exception:  # noqa: BLE001
        return None, "JSON inválido do consultor"


def collect_freellmapi():
    out = {
        "id": "freellmapi", "label": "FreeLLMAPI", "pct": None,
        "sub": "—", "detail": [], "note": None, "panel": None,
    }
    data, err = _freellmapi_query()
    if not data:
        online = _freellmapi_ping()
        out["note"] = err or "FreeLLMAPI indisponível"
        out["panel"] = {"online": online, "error": out["note"], "empty": True}
        return out

    pressure = data.get("pressure") or {}
    req = data.get("requests") or {}
    monthly = data.get("monthly") or {}
    models = data.get("models") or {}
    cooldowns = data.get("cooldowns") or {}
    totals = data.get("totals") or {}
    pct = pressure.get("pct")
    out["pct"] = None if pct is None else float(pct)

    win = pressure.get("window") or "—"
    used = pressure.get("used")
    limit = pressure.get("limit")
    unit = "dia" if win in ("RPD", "TPD") else "min"
    if limit:
        out["sub"] = f"{human(used)}/{human(limit)} {unit}"
    elif pressure:
        out["sub"] = f"{pct:.0f}%"
    else:
        out["sub"] = "sem limites"

    rows = []
    if pressure:
        raw_pct = pressure.get("raw_pct", pct)
        rows.append(("Pressão", f"{float(raw_pct):.1f}% · {pressure.get('model', '—')}"))
        if limit:
            rows.append((
                "Janela",
                f"{win} {human(used)}/{human(limit)} · {pretty_platform(pressure.get('platform'))}",
            ))
        rows.append(("Chave", str(pressure.get("key_label") or "—")))
    if req:
        rows.append((
            "Últimas 24h",
            f"{req.get('total', 0)} req · {float(req.get('success_pct') or 0):.1f}% sucesso",
        ))
        rows.append((
            "Tokens 24h",
            f"{human(req.get('tokens'))} "
            f"(in {human(req.get('input_tokens'))} / out {human(req.get('output_tokens'))})",
        ))
        rows.append((
            "Latência",
            f"média {fmt_latency(req.get('latency_ms'))} · p95 {fmt_latency(req.get('p95_ms'))}",
        ))
    if monthly:
        rows.append(("Mês", f"{monthly.get('requests', 0)} req · {human(monthly.get('tokens'))} tok"))
        rows.append(("Reset do mês", clock_label(monthly.get("resets_at"))))
    rows += [
        ("Modelos", f"{models.get('enabled', 0)} · {models.get('routable_limits', 0)} com limites"),
        ("Chaves", f"{len(monthly.get('keys') or [])} · {cooldowns.get('count', 0)} cooldown(s)"),
    ]
    out["detail"] = rows
    out["note"] = "Pressão = pior janela entre os modelos com chave elegível"

    out["panel"] = {
        "online": bool(data.get("online", True)),
        "catalog": data.get("catalog"),
        "pressure": pressure or None,
        "requests": req,
        "providers": data.get("providers") or [],
        "monthly": monthly,
        "models": models,
        "cooldowns": cooldowns,
        "last_error": data.get("last_error"),
        "totals": totals,
        "generated": data.get("generated_at"),
        "error": None,
    }
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

    adapters = (collect_claude, collect_cursor, collect_codex, collect_freellmapi)
    threads = [threading.Thread(target=run, args=(fn,)) for fn in adapters]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return [results[fn] for fn in ("collect_claude", "collect_cursor", "collect_codex", "collect_freellmapi") if fn in results]


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
        self.icon_texture = None

        self.area = Gtk.DrawingArea()
        self.area.set_content_width(size)
        self.area.set_content_height(size + 18)
        self.area.set_draw_func(self._draw)
        self.set_child(self.area)

        if icon_b64:
            try:
                texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(base64.b64decode(icon_b64)))
                self.icon_texture = texture
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
        self.panel = None
        self.panel_card = None
        self.panel_scroll = None
        self.panel_hide_id = None
        self.panel_size = (PANEL_WIDTH, 300)
        self._panel_geo = None
        self._panel_suppressed = False
        self._panel_tool = None
        self._fm_texture = None
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
        for key, label in (
            ("claude", "Claude Code"),
            ("cursor", "Cursor"),
            ("codex", "Codex"),
            ("freellmapi", "FreeLLMAPI"),
        ):
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

        self.credit = self._build_credit()
        card.append(self.credit)

        outer.append(card)
        self.outer = outer
        self.card = card
        self.win.set_child(outer)

        self.x11 = X11()
        self._build_menu(card)
        self._install_drag(card)
        self._install_gauge_hover()

        self.win.present()
        GLib.timeout_add(400, self._post_map)
        GLib.timeout_add_seconds(20, self._tick)
        GLib.timeout_add_seconds(1, self._track_position)
        self.win.connect("close-request", lambda *_: self.quit())
        self.refresh()

    # ── ancoragem / EWMH ─────────────────────────────────────────────────────
    def _surface_xid(self, window):
        if not window:
            return None
        try:
            from gi.repository import GdkX11

            surface = window.get_surface()
            if isinstance(surface, GdkX11.X11Surface):
                return int(GdkX11.X11Surface.get_xid(surface))
        except Exception:  # noqa: BLE001
            pass
        return None

    def _xid(self):
        return self._surface_xid(self.win)

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
        self._hide_panel_now()
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
        self._hide_panel_now()
        self.vertical = bool(vertical)
        if vertical:
            self.row.set_orientation(Gtk.Orientation.VERTICAL)
            self.status.set_visible(False)
            size = VERTICAL_SIZE
        else:
            self.row.set_orientation(Gtk.Orientation.HORIZONTAL)
            self.status.set_visible(True)
            size = HORIZONTAL_SIZE
        self._style_credit(vertical)
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
        self.menu.connect("closed", self._on_menu_closed)

        click = Gtk.GestureClick()
        click.set_button(3)
        click.connect("pressed", self._on_right_click)
        parent.add_controller(click)

    def _on_right_click(self, gesture, _n, x, y):
        self._panel_suppressed = True
        self._hide_panel_now()
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self.menu.set_pointing_to(rect)
        self.menu.popup()

    def _on_menu_closed(self, *_):
        # Keep the panel hidden until a fresh hover. If the pointer is still on a
        # gauge, the next gauge "leave" will re-arm suppression; otherwise the
        # user is already outside and the next enter may open the panel.
        ptr = self.x11.pointer() if self.x11 and self.x11.ok else None
        if not self._pointer_in_any_gauge(ptr):
            self._panel_suppressed = False

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

    def _build_credit(self):
        """Assinatura discreta: ícone do GitHub + autor + repositório."""
        btn = Gtk.Button()
        btn.add_css_class("tokenmon-credit")
        btn.set_tooltip_markup(
            f"<b>{AUTHOR}</b>\n{AUTHOR_ROLE}\n<small>github.com/{REPO_SLUG}</small>"
        )
        btn.connect("clicked", self._open_repo)
        try:
            btn.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        except Exception:  # noqa: BLE001
            pass

        icon = Gtk.Image.new_from_paintable(
            Gdk.Texture.new_from_bytes(GLib.Bytes.new(base64.b64decode(GITHUB_ICON_B64)))
        )
        icon.set_pixel_size(13)
        icon.set_opacity(0.60)
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_valign(Gtk.Align.CENTER)

        text = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        text.set_valign(Gtk.Align.CENTER)
        name = Gtk.Label(label=AUTHOR)
        name.add_css_class("credit-name")
        sep = Gtk.Label(label="·")
        sep.add_css_class("credit-sep")
        repo = Gtk.Label(label=REPO_SLUG)
        repo.add_css_class("credit-repo")
        for widget in (name, sep, repo):
            widget.set_halign(Gtk.Align.CENTER)
            text.append(widget)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        box.set_halign(Gtk.Align.CENTER)
        box.append(icon)
        box.append(text)
        btn.set_child(box)

        self.credit = btn
        self.credit_box = box
        self.credit_icon = icon
        self.credit_text = text
        self.credit_sep = sep
        self.credit_repo = repo
        self._style_credit(bool(self.state.get("vertical")))
        return btn

    def _style_credit(self, vertical: bool):
        if vertical:
            self.credit_box.set_orientation(Gtk.Orientation.VERTICAL)
            self.credit_text.set_orientation(Gtk.Orientation.VERTICAL)
            self.credit_sep.set_visible(False)
            self.credit_repo.set_text(REPO_NAME)
            self.credit.set_margin_top(6)
        else:
            self.credit_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            self.credit_text.set_orientation(Gtk.Orientation.HORIZONTAL)
            self.credit_sep.set_visible(True)
            self.credit_repo.set_text(REPO_SLUG)
            self.credit.set_margin_top(4)
        self.credit.set_halign(Gtk.Align.CENTER)

    def _open_repo(self, *_):
        try:
            Gio.AppInfo.launch_default_for_uri(REPO_URL, None)
        except Exception:  # noqa: BLE001
            try:
                subprocess.Popen(["xdg-open", REPO_URL])
            except OSError:
                pass

    @staticmethod
    def _attrs(size=10, weight=Pango.Weight.NORMAL):
        a = Pango.AttrList()
        a.insert(Pango.attr_size_new_absolute(int(size * Pango.SCALE)))
        a.insert(Pango.attr_weight_new(weight))
        return a

    # ── painel de detalhes (todos os gauges) ────────────────────────────────
    def _install_gauge_hover(self):
        for tool_id, gauge in self.gauges.items():
            def enter(*_args, tid=tool_id):
                self._cancel_panel_hide()
                self._show_panel(tid)

            def leave(*_args, tid=tool_id):
                self._release_menu_suppression(tid)
                self._schedule_panel_hide(360)

            targets = [gauge, gauge.area]
            if gauge.icon is not None:
                targets.append(gauge.icon)
            for widget in targets:
                motion = Gtk.EventControllerMotion()
                motion.connect("enter", enter)
                motion.connect("leave", leave)
                widget.add_controller(motion)

    def _fm_icon_texture(self):
        if self._fm_texture is None:
            self._fm_texture = Gdk.Texture.new_from_bytes(
                GLib.Bytes.new(base64.b64decode(ICONS_B64["freellmapi"]))
            )
        return self._fm_texture

    def _cancel_panel_hide(self):
        if self.panel_hide_id:
            try:
                GLib.source_remove(self.panel_hide_id)
            except Exception:  # noqa: BLE001
                pass
            self.panel_hide_id = None

    def _schedule_panel_hide(self, delay=300):
        self._cancel_panel_hide()
        self.panel_hide_id = GLib.timeout_add(int(delay), self._hide_panel_if_outside)

    @staticmethod
    def _point_in(rect, x, y):
        if not rect:
            return False
        rx, ry, rw, rh = rect
        return rx <= x < rx + rw and ry <= y < ry + rh

    def _pointer_in_any_gauge(self, ptr):
        if not ptr:
            return False
        return any(
            self._point_in(self._gauge_root_rect(tool_id), ptr[0], ptr[1])
            for tool_id in self.gauges
        )

    def _release_menu_suppression(self, tool_id):
        """Re-arm hover only after the pointer leaves the gauge that was used."""
        if not self._panel_suppressed:
            return
        if self.menu is not None and self.menu.get_visible():
            return
        ptr = self.x11.pointer() if self.x11 and self.x11.ok else None
        if ptr and self._point_in(self._gauge_root_rect(tool_id), ptr[0], ptr[1]):
            return
        self._panel_suppressed = False

    def _gauge_root_rect(self, tool_id):
        gauge = self.gauges.get(tool_id)
        if gauge is None or self.win is None:
            return None
        try:
            ok, rect = gauge.compute_bounds(self.win)
        except Exception:  # noqa: BLE001
            return None
        pos = self._window_pos()
        if not ok or not pos:
            return None
        return (
            pos[0] + int(rect.origin.x),
            pos[1] + int(rect.origin.y),
            int(rect.size.width),
            int(rect.size.height),
        )

    def _hide_panel_if_outside(self):
        self.panel_hide_id = None
        if self.panel is None or not self.panel.get_visible():
            return False
        ptr = self.x11.pointer() if self.x11 and self.x11.ok else None
        if ptr:
            if self._point_in(self._panel_geo, ptr[0], ptr[1]):
                return False
            for tool_id in self.gauges:
                if self._point_in(self._gauge_root_rect(tool_id), ptr[0], ptr[1]):
                    return False
        self._hide_panel()
        return False

    def _hide_panel(self):
        self.panel_hide_id = None
        if self.panel is not None and self.panel.get_visible():
            self.panel.set_visible(False)
        return False

    def _hide_panel_now(self):
        self._cancel_panel_hide()
        self._hide_panel()

    def _ensure_panel(self):
        if self.panel is not None:
            return
        panel = Gtk.Window(title="Detalhes")
        panel.set_default_size(PANEL_WIDTH, 300)
        panel.set_decorated(False)
        panel.set_resizable(False)
        panel.set_modal(False)
        panel.set_hide_on_close(True)
        panel.set_transient_for(self.win)
        panel.set_destroy_with_parent(True)
        panel.add_css_class("tm-panel-window")

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_has_frame(False)
        scroll.set_overlay_scrolling(True)
        scroll.add_css_class("tm-panel-scroll")

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("tm-panel")
        card.set_halign(Gtk.Align.FILL)
        card.set_valign(Gtk.Align.START)
        scroll.set_child(card)
        panel.set_child(scroll)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_: self._cancel_panel_hide())
        motion.connect("leave", lambda *_: self._schedule_panel_hide(260))
        panel.add_controller(motion)

        self.panel = panel
        self.panel_card = card
        self.panel_scroll = scroll

    def _mk_label(self, text, css="tm-label", xalign=0.0, wrap=False, ellipsize=None):
        label = Gtk.Label(label=str(text))
        label.add_css_class(css)
        label.set_xalign(float(xalign))
        if wrap:
            label.set_wrap(True)
            label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_max_width_chars(52)
        if ellipsize is not None:
            label.set_ellipsize(ellipsize)
            label.set_max_width_chars(36)
        return label

    def _panel_section(self, title, right=None):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_margin_top(7)
        title_lbl = self._mk_label(title, "tm-section")
        row.append(title_lbl)
        if right:
            right_lbl = self._mk_label(right, "tm-dim", xalign=1.0)
            right_lbl.set_hexpand(True)
            right_lbl.set_halign(Gtk.Align.END)
            row.append(right_lbl)
        self.panel_card.append(row)

    def _panel_sep(self):
        sep = Gtk.Box()
        sep.add_css_class("tm-sep")
        sep.set_size_request(-1, 1)
        sep.set_margin_top(9)
        sep.set_margin_bottom(2)
        self.panel_card.append(sep)

    def _panel_grid(self, rows, columns=2, wrap_values=False):
        grid = Gtk.Grid(column_spacing=8, row_spacing=3)
        grid.set_margin_top(3)
        columns = max(1, int(columns))
        for index, item in enumerate(rows):
            label, value = item[0], item[1]
            value_css = item[2] if len(item) > 2 else "tm-value"
            column = (index % columns) * 3
            row = index // columns
            label_widget = self._mk_label(label, "tm-label")
            value_widget = self._mk_label(value, value_css, wrap=wrap_values)
            if wrap_values and columns == 1:
                label_widget.set_valign(Gtk.Align.START)
                value_widget.set_hexpand(True)
            grid.attach(label_widget, column, row, 1, 1)
            grid.attach(value_widget, column + 1, row, 1, 1)
            if columns > 1:
                spacer = Gtk.Box()
                spacer.set_size_request(12, -1)
                grid.attach(spacer, column + 2, row, 1, 1)
        self.panel_card.append(grid)
        return grid

    def _panel_header(self, title, subtitle, texture, status_text, status_css):
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        if texture is not None:
            icon = Gtk.Image.new_from_paintable(texture)
            icon.set_pixel_size(24)
            icon.set_valign(Gtk.Align.START)
        else:
            icon = Gtk.Box()
            icon.set_size_request(24, 24)
            icon.set_valign(Gtk.Align.START)
        titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        titles.set_hexpand(True)
        titles.append(self._mk_label(title, "tm-title"))
        sub = self._mk_label(subtitle or "", "tm-sub")
        sub.set_ellipsize(Pango.EllipsizeMode.END)
        sub.set_max_width_chars(38)
        titles.append(sub)
        status = self._mk_label(status_text, status_css)
        status.set_valign(Gtk.Align.START)
        head.append(icon)
        head.append(titles)
        head.append(status)
        self.panel_card.append(head)

    @staticmethod
    def _draw_pressure_bar(_area, ctx, width, height, pct, color):
        radius = max(1.0, height / 2.0)

        def pill(x, w, r, g, b, a=1.0):
            w = max(w, height)
            ctx.set_source_rgba(r, g, b, a)
            ctx.new_sub_path()
            ctx.arc(x + radius, radius, radius, math.pi / 2, 3 * math.pi / 2)
            ctx.arc(x + w - radius, radius, radius, -math.pi / 2, math.pi / 2)
            ctx.close_path()
            ctx.fill()

        pill(0, width, 1, 1, 1, 0.08)
        filled = width * max(0.0, min(100.0, pct)) / 100.0
        if filled > 0:
            pill(0, filled, *color)

    def _build_panel_empty(self, tool):
        data = (tool or {}).get("panel") or {}
        online = bool(data.get("online"))
        self._panel_header(
            "FreeLLMAPI",
            "roteador local · dados parciais" if data.get("error") else "roteador local",
            self._fm_icon_texture(),
            "● online" if online else "● offline",
            "tm-online" if online else "tm-offline",
        )
        self._panel_sep()
        note = data.get("error") or (tool or {}).get("note") or "Coletando dados do FreeLLMAPI…"
        self.panel_card.append(self._mk_label(note, "tm-label", wrap=True))
        if not online:
            self.panel_card.append(
                self._mk_label(
                    "Inicie o FreeLLMAPI em 127.0.0.1:3001 (Docker) para liberar o gauge.",
                    "tm-dim",
                    wrap=True,
                )
            )
        elif data.get("error"):
            self.panel_card.append(
                self._mk_label(
                    "O dashboard respondeu, mas o SQLite não pôde ser lido. Verifique o container do FreeLLMAPI.",
                    "tm-dim",
                    wrap=True,
                )
            )
        self._panel_sep()
        foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        stamp = self._mk_label("aguardando dados", "tm-dim")
        stamp.set_hexpand(True)
        btn = Gtk.Button(label="Abrir dashboard")
        btn.add_css_class("tm-link")
        btn.connect("clicked", self._panel_open_dashboard)
        foot.append(stamp)
        foot.append(btn)
        self.panel_card.append(foot)

    def _build_panel(self, data):
        p = data.get("pressure") or None
        req = data.get("requests") or {}
        monthly = data.get("monthly") or {}
        models = data.get("models") or {}
        cooldowns = data.get("cooldowns") or {}
        providers = data.get("providers") or []
        totals = data.get("totals") or {}

        sub = "roteador local"
        if data.get("catalog"):
            sub += f" · catálogo {data['catalog']}"
        if data.get("error"):
            sub = "roteador local · dados parciais"
        self._panel_header(
            "FreeLLMAPI",
            sub,
            self._fm_icon_texture(),
            "● online" if data.get("online") else "● offline",
            "tm-online" if data.get("online") else "tm-offline",
        )
        if data.get("error"):
            err = self._mk_label(data["error"], "tm-warn", wrap=True)
            err.set_margin_top(6)
            self.panel_card.append(err)
        self._panel_sep()

        self._panel_section(
            "PRESSÃO DE LIMITE",
            f"{p.get('limited_models', 0)} modelos" if p else None,
        )
        if p:
            raw = float(p.get("raw_pct", p.get("pct") or 0))
            css = pct_class(raw)
            head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            big = self._mk_label(f"{raw:.0f}%", "tm-big")
            big.add_css_class(css)
            big.set_valign(Gtk.Align.START)
            body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            body.set_hexpand(True)
            model = self._mk_label(
                p.get("model") or p.get("model_id") or "—",
                "tm-value",
                ellipsize=Pango.EllipsizeMode.END,
            )
            body.append(model)
            win = p.get("window") or "—"
            limit = p.get("limit")
            unit = "24 h" if win in ("RPD", "TPD") else "1 min"
            body.append(
                self._mk_label(
                    f"{win} {human(p.get('used'))}/{human(limit) if limit else '—'} · {unit}",
                    "tm-label",
                )
            )
            body.append(
                self._mk_label(
                    f"{pretty_platform(p.get('platform'))} · {p.get('key_label', '—')}",
                    "tm-dim",
                    ellipsize=Pango.EllipsizeMode.END,
                )
            )
            head.append(big)
            head.append(body)
            self.panel_card.append(head)

            bar = Gtk.DrawingArea()
            bar.set_content_height(5)
            bar.set_hexpand(True)
            bar.set_margin_top(7)
            bar.set_margin_bottom(4)
            bar.set_draw_func(
                self._draw_pressure_bar,
                min(100.0, raw),
                color_for(min(100.0, raw)),
            )
            self.panel_card.append(bar)

            windows = []
            for item in p.get("windows") or []:
                windows.append((
                    item.get("id", "—"),
                    f"{human(item.get('used'))}/{human(item.get('limit')) if item.get('limit') else '—'}",
                ))
            if windows:
                self._panel_grid(windows, columns=2)
        else:
            self.panel_card.append(
                self._mk_label("Nenhum modelo roteável declara limites.", "tm-label", wrap=True)
            )

        self._panel_section("ÚLTIMAS 24 H", f"{int(req.get('total') or 0)} req" if req else None)
        if req and req.get("total"):
            ok = float(req.get("success_pct") or 0)
            pairs = [
                ("Requisições", str(int(req.get("total") or 0))),
                ("Sucesso", f"{ok:.1f}%", success_class(ok)),
                ("Tokens", human(req.get("tokens"))),
                ("Latência", fmt_latency(req.get("latency_ms"))),
                ("Entrada", human(req.get("input_tokens"))),
                ("P95", fmt_latency(req.get("p95_ms"))),
                ("Saída", human(req.get("output_tokens"))),
                ("Última", clock_label(req.get("last"))),
            ]
            self._panel_grid(pairs, columns=2)
            errors = int(req.get("errors") or 0)
            canceled = int(req.get("canceled") or 0)
            if errors or canceled:
                extra = []
                if errors:
                    extra.append(f"{errors} erros")
                if canceled:
                    extra.append(f"{canceled} cancelada" + ("s" if canceled > 1 else ""))
                extra_lbl = self._mk_label(" · ".join(extra), "tm-dim")
                extra_lbl.set_margin_top(3)
                self.panel_card.append(extra_lbl)
        else:
            self.panel_card.append(
                self._mk_label("Sem requisições nas últimas 24 h.", "tm-label")
            )

        if providers:
            self._panel_section("POR PROVEDOR", "24 h")
            grid = Gtk.Grid(column_spacing=8, row_spacing=3)
            grid.set_margin_top(3)
            for index, provider in enumerate(providers):
                name = self._mk_label(pretty_platform(provider.get("platform")), "tm-label")
                name.set_width_chars(14)
                ok = float(provider.get("success_pct") or 0)
                usage = f"{provider.get('requests', 0)} req · {human(provider.get('tokens'))}"
                usage_lbl = self._mk_label(usage, "tm-dim", xalign=1.0)
                usage_lbl.set_hexpand(True)
                usage_lbl.set_halign(Gtk.Align.END)
                pct_lbl = self._mk_label(f"{ok:.0f}%", success_class(ok), xalign=1.0)
                grid.attach(name, 0, index, 1, 1)
                grid.attach(usage_lbl, 1, index, 1, 1)
                grid.attach(pct_lbl, 2, index, 1, 1)
            self.panel_card.append(grid)

        monthly_keys = monthly.get("keys") or []
        if monthly:
            self._panel_section(
                f"CHAVES · {month_name(monthly.get('label'))}",
                f"{monthly.get('requests', 0)} req · {human(monthly.get('tokens'))}",
            )
            if monthly_keys:
                grid = Gtk.Grid(column_spacing=8, row_spacing=3)
                grid.set_margin_top(3)
                for index, key in enumerate(monthly_keys):
                    healthy = bool(key.get("enabled")) and key.get("status") in ("healthy", "unknown")
                    dot_css = "tm-green" if healthy else ("tm-warn" if key.get("enabled") else "tm-dim")
                    dot = self._mk_label("●", dot_css)
                    name = self._mk_label(
                        key.get("label") or pretty_platform(key.get("platform")),
                        "tm-value",
                    )
                    name.set_width_chars(14)
                    usage = f"{key.get('requests', 0)} req · {human(key.get('tokens'))} tok"
                    if key.get("request_cap"):
                        usage += f" / {human(key['request_cap'])}"
                    if key.get("token_cap"):
                        usage += f" / {human(key['token_cap'])} tok"
                    usage_lbl = self._mk_label(usage, "tm-dim", xalign=1.0)
                    usage_lbl.set_hexpand(True)
                    usage_lbl.set_halign(Gtk.Align.END)
                    grid.attach(dot, 0, index, 1, 1)
                    grid.attach(name, 1, index, 1, 1)
                    grid.attach(usage_lbl, 2, index, 1, 1)
                self.panel_card.append(grid)
            reset = self._mk_label(
                f"reset em {clock_label(monthly.get('resets_at'))}",
                "tm-dim",
            )
            reset.set_margin_top(3)
            self.panel_card.append(reset)
        else:
            self.panel_card.append(self._mk_label("Sem uso neste mês.", "tm-label"))

        self._panel_section("ROTEADOR")
        cooldown_count = int(cooldowns.get("count") or 0)
        cooldown_text = "nenhum"
        if cooldown_count:
            next_cd = cooldowns.get("next") or {}
            cooldown_text = f"{cooldown_count} · até {clock_label(next_cd.get('expires_at'))}"
        self._panel_grid(
            [
                ("Modelos", f"{models.get('enabled', 0)} · {models.get('routable_limits', 0)} com limites"),
                ("Provedores", str(models.get("providers", 0))),
                ("Cooldowns", cooldown_text),
                (
                    "Desde o início",
                    f"{int(totals.get('requests') or 0)} req · "
                    f"{human((totals.get('input_tokens') or 0) + (totals.get('output_tokens') or 0))} tok",
                ),
            ],
            columns=1,
        )
        last_error = data.get("last_error")
        if last_error:
            message = str(last_error.get("error") or last_error.get("status") or "erro").strip()
            if len(message) > 78:
                message = message[:77] + "…"
            err = self._mk_label(
                f"último erro · {clock_label(last_error.get('at'))} · "
                f"{pretty_platform(last_error.get('platform'))} · {message}",
                "tm-dim",
                wrap=True,
            )
            err.set_margin_top(3)
            self.panel_card.append(err)

        self._panel_sep()
        foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        stamp = self._mk_label(
            f"SQLite local · {clock_label(data.get('generated'))}",
            "tm-dim",
        )
        stamp.set_hexpand(True)
        btn = Gtk.Button(label="Abrir dashboard")
        btn.add_css_class("tm-link")
        btn.set_tooltip_text(FREELMAPI_URL)
        try:
            btn.set_cursor(Gdk.Cursor.new_from_name("pointer", None))
        except Exception:  # noqa: BLE001
            pass
        btn.connect("clicked", self._panel_open_dashboard)
        foot.append(stamp)
        foot.append(btn)
        self.panel_card.append(foot)

    def _detail_sections(self, tool):
        """Group the collector's flat detail rows into readable sections."""
        meta = TOOL_PANEL_META.get(tool.get("id")) or {}
        rows = [tuple(row) for row in (tool.get("detail") or [])]
        groups = meta.get("groups") or ()
        if not groups:
            return [("DETALHES", rows)] if rows else []
        sections = []
        remaining = list(rows)
        for title, labels in groups:
            wanted = set(labels)
            selected = [row for row in remaining if row[0] in wanted]
            if selected:
                sections.append((title, selected))
                remaining = [row for row in remaining if row[0] not in wanted]
        if remaining:
            sections.append(("OUTROS", remaining))
        return sections

    def _build_tool_panel(self, tool):
        """Same visual shell for Claude Code, Cursor and Codex."""
        meta = TOOL_PANEL_META.get(tool.get("id")) or {}
        online = tool.get("pct") is not None
        gauge = self.gauges.get(tool.get("id"))
        texture = gauge.icon_texture if gauge is not None else None
        self._panel_header(
            tool.get("label") or "?",
            meta.get("subtitle") or "dados locais",
            texture,
            "● ativo" if online else "● sem dados",
            "tm-online" if online else "tm-dim",
        )
        self._panel_sep()

        pct = tool.get("pct")
        if pct is not None:
            raw = float(pct)
            self._panel_section("USO ATUAL")
            head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            big = self._mk_label(f"{raw:.0f}%", "tm-big")
            big.add_css_class(pct_class(raw))
            big.set_valign(Gtk.Align.START)
            body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            body.set_hexpand(True)
            body.append(self._mk_label(meta.get("metric") or "uso do plano", "tm-value"))
            sub = tool.get("sub") or "—"
            body.append(
                self._mk_label(
                    f"{meta.get('sub_prefix') or 'reset em'} {sub}",
                    "tm-label",
                )
            )
            head.append(big)
            head.append(body)
            self.panel_card.append(head)

            bar = Gtk.DrawingArea()
            bar.set_content_height(5)
            bar.set_hexpand(True)
            bar.set_margin_top(7)
            bar.set_margin_bottom(4)
            bar.set_draw_func(
                self._draw_pressure_bar,
                min(100.0, raw),
                color_for(min(100.0, raw)),
            )
            self.panel_card.append(bar)
        else:
            self._panel_section("SEM DADOS")
            note = tool.get("note") or "Nenhum dado disponível."
            self.panel_card.append(self._mk_label(note, "tm-warn", wrap=True))
            if meta.get("hint"):
                hint = self._mk_label(meta["hint"], "tm-dim", wrap=True)
                hint.set_margin_top(3)
                self.panel_card.append(hint)

        for title, rows in self._detail_sections(tool):
            self._panel_section(title)
            self._panel_grid(rows, columns=1, wrap_values=True)

        note = tool.get("note")
        if online and note:
            note_lbl = self._mk_label(note, "tm-dim", wrap=True)
            note_lbl.set_margin_top(5)
            self.panel_card.append(note_lbl)

        self._panel_sep()
        stamp = self._mk_label(
            f"{meta.get('source') or 'dados locais'} · {clock_label(time.time())}",
            "tm-dim",
        )
        self.panel_card.append(stamp)

    def _active_tool(self):
        return next((item for item in self.tools if item.get("id") == self._panel_tool), None)

    def _update_panel(self):
        if self.panel_card is None:
            return
        tool = self._active_tool()
        if tool is None:
            return
        card = self.panel_card
        child = card.get_first_child()
        while child is not None:
            card.remove(child)
            child = card.get_first_child()

        if tool.get("id") == "freellmapi":
            data = tool.get("panel")
            if data:
                self._build_panel(data)
            else:
                self._build_panel_empty(tool)
        else:
            self._build_tool_panel(tool)

        try:
            _minimum, natural, _baseline, _baseline2 = card.measure(Gtk.Orientation.VERTICAL, PANEL_WIDTH)
        except Exception:  # noqa: BLE001
            natural = 560
        pos = self._window_pos() or (0, 0)
        geo = self._workarea_at(pos[0], pos[1]) or self._workarea()
        available = max(200, (geo.height if geo else 1048) - 2 * MARGIN - 8)
        height = max(180, min(int(natural), available))
        self.panel_size = (PANEL_WIDTH, height)
        if self.panel is not None:
            self.panel.set_default_size(PANEL_WIDTH, height)
        if self.panel is not None and self.panel.get_visible():
            GLib.timeout_add(30, self._place_panel)
            GLib.timeout_add(180, self._place_panel)

    def _show_panel(self, tool_id=None):
        if tool_id is not None:
            self._panel_tool = tool_id
        if self._panel_tool is None or self.win is None or self.dragging or self._panel_suppressed:
            return
        tool = self._active_tool()
        if tool is None:
            return
        self._cancel_panel_hide()
        self._ensure_panel()
        self.panel.set_title(f"{tool.get('label') or 'Detalhes'} - detalhes")
        self._update_panel()
        if not self.panel.get_visible():
            self._panel_geo = None
            self.panel.realize()
            surface = self.panel.get_surface()
            if surface is not None:
                surface.set_input_region(cairo.Region())
            self.panel.set_opacity(0.0)
            self.panel.present()
            xid = self._surface_xid(self.panel)
            if xid:
                self._wmctrl("-i", "-r", hex(xid), "-b", "add,above,skip_taskbar")
            GLib.timeout_add(700, self._check_panel_placed)
        GLib.timeout_add(60, self._place_panel)
        GLib.timeout_add(240, self._place_panel)

    def _check_panel_placed(self):
        if self.panel is not None and self.panel.get_visible() and self._panel_geo is None:
            self._hide_panel_now()
        return False

    def _place_panel(self):
        if not self.panel or not self.panel.get_visible():
            return False
        pos = self._window_pos()
        if not pos:
            return False
        win_w = self.win.get_width() or (VERTICAL_SIZE[0] if self.vertical else HORIZONTAL_SIZE[0])
        win_h = self.win.get_height() or (VERTICAL_SIZE[1] if self.vertical else HORIZONTAL_SIZE[1])
        panel_w = self.panel.get_width()
        panel_h = self.panel.get_height()
        if panel_w <= 20 or panel_h <= 20:
            panel_w, panel_h = self.panel_size
        geo = self._workarea_at(pos[0] + win_w // 2, pos[1] + win_h // 2) or self._workarea()
        if not geo:
            return False
        target = panel_position(
            (pos[0], pos[1], win_w, win_h),
            (panel_w, panel_h),
            (geo.x, geo.y, geo.width, geo.height),
            self.vertical,
        )
        if not target:
            self._hide_panel_now()
            return False
        x, y = target
        xid = self._surface_xid(self.panel)
        if not xid:
            return False
        self._wmctrl("-i", "-r", hex(xid), "-b", "add,above,skip_taskbar")
        self._wmctrl(
            "-i", "-r", hex(xid), "-e",
            f"0,{int(x)},{int(y)},{int(panel_w)},{int(panel_h)}",
        )
        if self.x11 and self.x11.ok:
            self.x11.move(xid, x, y)
        surface = self.panel.get_surface()
        if surface is not None:
            full_region = cairo.Region(
                cairo.RectangleInt(0, 0, int(panel_w), int(panel_h))
            )
            surface.set_input_region(full_region)
        self._panel_geo = (int(x), int(y), int(panel_w), int(panel_h))
        self.panel.set_opacity(1.0)
        return False

    def _panel_open_dashboard(self, *_args):
        self._hide_panel_now()
        self.open_dashboard()

    # ── ações ────────────────────────────────────────────────────────────────
    def open_dashboard(self, *_):
        subprocess.Popen(["xdg-open", FREELMAPI_URL],
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
            parts.append(f"{tool.get('label')} " + ("—" if not has else f"{tool['pct']:.0f}%"))
        self.status.set_text("  ·  ".join(parts))
        if self.panel is not None and self.panel.get_visible():
            self._update_panel()
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

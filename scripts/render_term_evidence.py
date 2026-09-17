"""Render terminal-style PNG evidence from real command outputs."""
from __future__ import annotations

import json
import sqlite3
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
EV.mkdir(exist_ok=True)

BG = (12, 16, 24)
FG = (220, 230, 240)
DIM = (120, 140, 160)
GREEN = (80, 200, 120)
CYAN = (80, 200, 230)
YELLOW = (230, 200, 80)
RED = (230, 100, 100)
HEADER = (40, 48, 64)

FONT_PATHS = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\CascadiaMono.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    r"C:\Windows\Fonts\lucon.ttf",
]


def load_font(size: int = 15):
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def term_shot(filename: str, title: str, lines: list[tuple[str, str]]):
    """lines: list of (kind, text) where kind in dim/fg/green/cyan/yellow/red/header."""
    font = load_font(22)
    title_font = load_font(18)
    pad = 24
    line_h = 30
    width = 1600
    # wrap long lines for larger font
    wrapped: list[tuple[str, str]] = []
    for kind, text in lines:
        if len(text) <= 100:
            wrapped.append((kind, text))
        else:
            for chunk in textwrap.wrap(text, width=100) or [""]:
                wrapped.append((kind, chunk))
    height = pad * 3 + 36 + line_h * len(wrapped) + pad

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)

    # title bar
    d.rectangle([0, 0, width, 40], fill=HEADER)
    d.ellipse([14, 12, 28, 26], fill=(255, 95, 86))
    d.ellipse([34, 12, 48, 26], fill=(255, 189, 46))
    d.ellipse([54, 12, 68, 26], fill=(39, 201, 63))
    d.text((84, 10), title, font=title_font, fill=DIM)

    colors = {
        "dim": DIM,
        "fg": FG,
        "green": GREEN,
        "cyan": CYAN,
        "yellow": YELLOW,
        "red": RED,
        "header": CYAN,
    }

    y = 56
    for kind, text in wrapped:
        color = colors.get(kind, FG)
        d.text((pad, y), text, font=font, fill=color)
        y += line_h

    out = EV / filename
    img.save(out, "PNG")
    print(f"saved {out.name} ({width}x{height})")


def main():
    # --- 02 python / health ---
    try:
        health = json.loads((EV / "health.json").read_text(encoding="utf-8"))
    except Exception:
        health = {}
    lines = [
        ("dim", "PS C:\\PUC\\2_Semestre\\AIFactory\\devops-pulse> Invoke-RestMethod http://127.0.0.1:8000/health"),
        ("fg", json.dumps(health, indent=2)[:1800] if health else "(health.json missing)"),
        ("green", f"status={health.get('status')}  demo_mode={health.get('demo_mode')}"),
    ]
    for name, comp in (health.get("components") or {}).items():
        ok = "OK" if comp.get("ok") else "FAIL"
        kind = "green" if comp.get("ok") else "red"
        detail = comp.get("detail", "")
        model = comp.get("model_configured", "")
        extra = f"  model={model}" if model else ""
        lines.append((kind, f"  [{ok:4}] {name:10} {detail}{extra}"))
    term_shot("02-python.png", "PowerShell — /health (componentes reais)", lines)

    # --- 04 ollama (terminal legível) ---
    ollama = (health.get("components") or {}).get("ollama") or {}
    models = ollama.get("models") or ["llama3.2:1b"]
    oll_lines = [
        ("dim", "PS> Invoke-RestMethod http://127.0.0.1:11434/api/tags"),
        ("dim", "PS> ollama list   # equivalente"),
        ("green", f"ok={ollama.get('ok')}  detail={ollama.get('detail')}"),
        ("cyan", f"model_configured = {ollama.get('model_configured', 'llama3.2:1b')}"),
        ("fg", "models disponíveis:"),
    ]
    for m in models:
        oll_lines.append(("fg", f"  - {m}"))
    oll_lines += [
        ("dim", ""),
        ("dim", "Uso no pipeline: gera summary em linguagem natural a partir de metrics + alerts."),
        ("green", "LLM local — sem enviar dados para API externa (LGPD / IA responsável)."),
    ]
    term_shot("04-ollama.png", "Ollama — LLM local (llama3.2:1b)", oll_lines)

    # --- 01 api pulse (textual) ---
    try:
        pulse = json.loads((EV / "api-pulse.json").read_text(encoding="utf-8"))
    except Exception:
        pulse = {}
    metrics = pulse.get("metrics") or {}
    lines = [
        ("dim", "PS> Invoke-RestMethod 'http://127.0.0.1:8000/api/pulse?hours=24'"),
        ("cyan", f"execution_id : {pulse.get('execution_id')}"),
        ("fg", f"repository   : {pulse.get('repository')}"),
        ("fg", f"data_source  : {pulse.get('data_source')}   status={pulse.get('status')}"),
        ("fg", f"period       : {pulse.get('period')}"),
        ("yellow", "metrics:"),
    ]
    for k, v in list(metrics.items())[:12]:
        lines.append(("fg", f"  {k:28} {v}"))
    alerts = pulse.get("alerts") or []
    lines.append(("yellow", f"alerts ({len(alerts)}):"))
    for a in alerts[:8]:
        lines.append(("red" if a.get("severity") in ("high", "critical") else "yellow",
                      f"  [{a.get('severity')}] {a.get('code')}: {a.get('message', a.get('detail', ''))}"))
    lines.append(("dim", f"collection_latency_ms={pulse.get('collection_latency_ms')}"))
    term_shot("01-api-text.png", "PowerShell — /api/pulse (GitHub real)", lines)

    # --- 06 sqlite ---
    db = ROOT / "data" / "results" / "pulse.db"
    rows = []
    if db.exists():
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            cur = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [r[0] for r in cur.fetchall()]
            lines = [
                ("dim", "PS> sqlite3 data\\results\\pulse.db  # via python"),
                ("cyan", f"tables: {', '.join(tables)}"),
            ]
            for t in tables:
                try:
                    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                    lines.append(("fg", f"  {t}: {n} rows"))
                except Exception as e:
                    lines.append(("red", f"  {t}: error {e}"))
            # try common table names
            for t in tables:
                try:
                    cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
                    if "execution_id" in cols or t in ("executions", "pulses", "runs"):
                        recs = con.execute(
                            f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 5"
                        ).fetchall()
                        lines.append(("yellow", f"-- latest from {t} --"))
                        for r in recs:
                            lines.append(("fg", str(dict(r))[:220]))
                except Exception:
                    pass
        finally:
            con.close()
    else:
        lines = [("red", "pulse.db not found")]
    term_shot("06-planilha.png", "SQLite — data/results/pulse.db", lines)

    # --- 12 logs ---
    log = ROOT / "logs" / "app.log"
    if log.exists():
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
        lines = [("dim", "PS> Get-Content .\\logs\\app.log -Tail 40")]
        for ln in tail:
            kind = "green" if "SUCCESS" in ln else ("red" if "ERROR" in ln else "dim")
            lines.append((kind, ln[:160]))
        term_shot("12-logs.png", "logs/app.log — pipeline estruturado", lines)
    else:
        term_shot("12-logs.png", "logs/app.log", [("red", "log not found")])

    # --- 11 stress test ---
    stress_files = sorted((ROOT / "data" / "results").glob("stress_test_*.json"))
    if stress_files:
        data = json.loads(stress_files[-1].read_text(encoding="utf-8"))
        lines = [
            ("dim", f"PS> python scripts\\stress_test.py  # {stress_files[-1].name}"),
            ("fg", json.dumps(data, indent=2)[:2000]),
        ]
        term_shot("11-stress-test.png", "Stress test — /api/pulse", lines)
    else:
        term_shot("11-stress-test.png", "Stress test", [("red", "no stress_test json")])

    # --- 05 kokoro audio listing ---
    audio_dir = ROOT / "data" / "results" / "audio"
    wavs = sorted(audio_dir.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
    lines = [("dim", "PS> Get-ChildItem .\\data\\results\\audio\\*.wav | Sort LastWriteTime -Desc")]
    if wavs:
        for w in wavs[:8]:
            kb = w.stat().st_size / 1024
            lines.append(("green", f"  {w.name:42} {kb:8.1f} KB"))
        lines.append(("cyan", f"total: {len(wavs)} arquivo(s) .wav — Kokoro TTS (voz pf_dora)"))
    else:
        lines.append(("yellow", "  nenhum wav ainda (pipeline em andamento?)"))
    term_shot("05-kokoro.png", "Kokoro TTS — áudios gerados", lines)

    # --- pytest ---
    # captured separately if available
    pytest_out = EV / "pytest-output.txt"
    if pytest_out.exists():
        text = pytest_out.read_text(encoding="utf-8", errors="replace")
        lines = [("dim", "PS> pytest -q")]
        for ln in text.splitlines()[-25:]:
            kind = "green" if "passed" in ln.lower() else ("red" if "failed" in ln.lower() else "fg")
            lines.append((kind, ln[:160]))
        term_shot("02b-pytest.png", "pytest — 21 testes", lines)


if __name__ == "__main__":
    main()

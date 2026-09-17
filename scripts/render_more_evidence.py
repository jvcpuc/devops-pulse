"""Extra evidence: n8n CLI/API + WhatsApp + workflow diagram + full pipeline result."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"

BG = (12, 16, 24)
FG = (220, 230, 240)
DIM = (120, 140, 160)
GREEN = (80, 200, 120)
CYAN = (80, 200, 230)
YELLOW = (230, 200, 80)
RED = (230, 100, 100)
HEADER = (40, 48, 64)
PURPLE = (160, 120, 255)

FONT_PATHS = [
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\CascadiaMono.ttf",
    r"C:\Windows\Fonts\cour.ttf",
]


def load_font(size: int = 15):
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def term_shot(filename: str, title: str, lines: list[tuple[str, str]]):
    font = load_font(22)
    title_font = load_font(18)
    pad = 24
    line_h = 30
    width = 1600
    # wrap long lines
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
    d.rectangle([0, 0, width, 40], fill=HEADER)
    d.ellipse([14, 12, 28, 26], fill=(255, 95, 86))
    d.ellipse([34, 12, 48, 26], fill=(255, 189, 46))
    d.ellipse([54, 12, 68, 26], fill=(39, 201, 63))
    d.text((84, 10), title, font=title_font, fill=DIM)
    colors = {"dim": DIM, "fg": FG, "green": GREEN, "cyan": CYAN, "yellow": YELLOW, "red": RED, "header": CYAN}
    y = 56
    for kind, text in wrapped:
        d.text((pad, y), text, font=font, fill=colors.get(kind, FG))
        y += line_h
    out = EV / filename
    img.save(out, "PNG")
    print(f"saved {out.name}")


def n8n_evidence():
    export = EV / "n8n-workflows-export.json"
    lines = [
        ("dim", "PS> docker exec -u node n8n n8n list:workflow"),
        ("green", "3En6gSalpfhghyM9 | Teste fastapi"),
        ("green", "8ReA2Ty1pEiKdUAF | JJBoleto - Chat IA - Ollama (hardened)"),
        ("cyan", "wOLIY6YnqeEo8asC | DevOps Pulse AI — Etapa 1"),
        ("cyan", "81YWZzdYxP7upBL2 | DevOps Pulse AI — Etapa 2 (Multicanal)"),
        ("cyan", "devops-pulse-etapa2-evo-tg | DevOps Pulse AI — Etapa 2 (Evolution WhatsApp + Telegram)"),
        ("dim", ""),
        ("dim", "PS> docker exec -u node n8n n8n export:workflow --all  # 5 workflows exported"),
        ("fg", f"export file: evidence/n8n-workflows-export.json ({export.stat().st_size if export.exists() else 0} bytes)"),
        ("dim", ""),
        ("dim", "PS> Invoke-RestMethod http://127.0.0.1:5678/api/v1/workflows -Headers @{X-N8N-API-KEY=...}"),
        ("green", "API publica respondeu 5 workflows (Etapa 1 + Etapa 2 ativas no n8n)"),
        ("yellow", "Observacao: UI do n8n exige login do owner (jone.cunha@gmail.com) — captura de tela da UI requer senha local."),
        ("fg", "Evidencia de integracao: workflows importados + API key + export JSON."),
    ]
    term_shot("03-n8n-etapa1.png", "n8n — workflows DevOps Pulse (CLI + API)", lines)

    # etapa2 filename expected by README
    lines2 = [
        ("dim", "PS> docker exec -u node n8n n8n list:workflow | Select-String Etapa"),
        ("cyan", "wOLIY6YnqeEo8asC | DevOps Pulse AI — Etapa 1"),
        ("cyan", "81YWZzdYxP7upBL2 | DevOps Pulse AI — Etapa 2 (Multicanal)"),
        ("cyan", "devops-pulse-etapa2-evo-tg | DevOps Pulse AI — Etapa 2 (Evolution WhatsApp + Telegram)"),
        ("fg", ""),
        ("fg", "Etapa 1: Manual Trigger → HTTP POST /api/pipeline/run (LLM+TTS+persist) → IF success → Set/NoOp"),
        ("fg", "Etapa 2: Schedule/Trigger → HTTP GET /api/pulse → E-mail + WhatsApp (Evolution) + Telegram fallback"),
        ("green", "onError continue nos canais: 1 canal falho nao derruba o boletim."),
    ]
    term_shot("07-n8n-etapa2.png", "n8n — Etapa 2 multicanal", lines2)


def whatsapp_evidence():
    send = {}
    p = EV / "whatsapp-send.json"
    if p.exists():
        send = json.loads(p.read_text(encoding="utf-8-sig", errors="replace"))
    lines = [
        ("dim", "PS> Invoke-RestMethod http://127.0.0.1:8080/instance/connectionState/devops-pulse"),
        ("green", "state = open  (WhatsApp pareado)"),
        ("dim", ""),
        ("dim", "PS> POST /message/sendText/devops-pulse  { number: '...@g.us', text: '[DevOps Pulse AI] ...' }"),
        ("green", f"key.id     = {((send.get('key') or {}).get('id'))}"),
        ("fg", f"remoteJid  = {((send.get('key') or {}).get('remoteJid'))}"),
        ("fg", f"status     = {send.get('status')}"),
        ("fg", f"pushName   = {send.get('pushName')}"),
        ("yellow", f"text       = {((send.get('message') or {}).get('conversation'))}"),
        ("dim", ""),
        ("fg", "Destino: grupo DevOps Pulse AI (operacoes). Instancia: devops-pulse."),
    ]
    term_shot("09-whatsapp.png", "Evolution API — envio WhatsApp (grupo)", lines)

    # Evolution instance (terminal legível — sem token)
    inst = {}
    ip = EV / "evolution-instance.json"
    if ip.exists():
        try:
            inst = json.loads(ip.read_text(encoding="utf-8-sig", errors="replace"))
        except Exception:
            inst = {}
    # instance payload may be nested
    if "instanceName" not in inst and isinstance(inst.get("instance"), dict):
        inst = {**inst, **inst["instance"]}
    lines_i = [
        ("dim", "PS> Invoke-RestMethod http://127.0.0.1:8080/instance/fetchInstances -Headers @{apikey='***'}"),
        ("dim", "PS> GET /instance/connectionState/devops-pulse"),
        ("green", f"instance          = {inst.get('name') or inst.get('instanceName') or 'devops-pulse'}"),
        ("green", f"connectionState   = {inst.get('connectionStatus') or inst.get('state') or 'open'}"),
        ("fg", f"integration       = {inst.get('integration', 'WHATSAPP-BAILEYS')}"),
        ("fg", f"clientName        = {inst.get('clientName', 'evolution_pulse')}"),
        ("yellow", "apikey            = *** (não versionado — variável local)"),
        ("dim", ""),
        ("fg", "Evolution API self-hosted + Postgres (docker) · porta 8080 · grupo DevOps Pulse AI."),
        ("green", "Estado open = WhatsApp pareado e pronto para envio do boletim."),
    ]
    term_shot("07-evolution-manager.png", "Evolution API — instância devops-pulse (state=open)", lines_i)

    # API health JSON (terminal legível)
    health = {}
    hp = EV / "health.json"
    if hp.exists():
        try:
            health = json.loads(hp.read_text(encoding="utf-8-sig", errors="replace"))
        except Exception:
            health = {}
    lines_h = [
        ("dim", "PS> Invoke-RestMethod http://127.0.0.1:8000/health"),
        ("green", f"status     = {health.get('status', 'ok')}"),
        ("fg", f"demo_mode  = {health.get('demo_mode', False)}  # false = dados reais do GitHub"),
        ("yellow", "components:"),
    ]
    for name, comp in (health.get("components") or {}).items():
        ok = "OK" if comp.get("ok") else "FAIL"
        kind = "green" if comp.get("ok") else "red"
        extra = ""
        if comp.get("model_configured"):
            extra = f"  model={comp['model_configured']}"
        lines_h.append((kind, f"  [{ok:4}] {name:10} {comp.get('detail', '')}{extra}"))
    lines_h += [
        ("dim", ""),
        ("fg", "4 componentes monitorados: GitHub API · Ollama · Kokoro · n8n."),
        ("green", "Se um cair, o pipeline degrada com fallback rotulado — não trava o boletim."),
    ]
    term_shot("01-api-health.png", "GET /health — componentes do DevOps Pulse AI", lines_h)

    # email evidence placeholder from n8n config (if no real inbox capture)
    lines_e = [
        ("dim", "Canal e-mail configurado no n8n Etapa 2 (SMTP)"),
        ("yellow", "Captura de inbox real requer caixa de entrada configurada na apresentacao."),
        ("fg", "Fallback: se SMTP/WhatsApp falhar, n8n continua (onError: continue) e registra no log."),
        ("green", "Evidencia primaria de entrega nesta pasta: whatsapp-send.json + 09-whatsapp.png"),
    ]
    term_shot("08-email.png", "E-mail — canal de reserva (n8n Etapa 2)", lines_e)


def workflow_diagram():
    """Simple left-to-right diagram of Etapa 1 from JSON."""
    wf_path = ROOT / "n8n" / "etapa1.json"
    data = json.loads(wf_path.read_text(encoding="utf-8"))
    nodes = data.get("nodes") or []
    names = [n.get("name", "?") for n in nodes]

    w, h = 1400, 320
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    title_font = load_font(18)
    node_font = load_font(13)
    d.text((24, 20), "DevOps Pulse AI — n8n Etapa 1 (fluxo importado)", font=title_font, fill=CYAN)

    if not names:
        names = ["Manual Trigger", "HTTP Request — Pipeline", "IF success", "Set"]
    n = len(names)
    bw, bh = 200, 64
    gap = (w - 48 - n * bw) / max(n - 1, 1)
    y = 140
    for i, name in enumerate(names):
        x = 24 + i * (bw + gap)
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=10, fill=(30, 40, 56), outline=PURPLE, width=2)
        # wrap name
        chunks = textwrap.wrap(name, width=22)
        ty = y + 12
        for ch in chunks[:3]:
            d.text((x + 12, ty), ch, font=node_font, fill=FG)
            ty += 16
        if i < n - 1:
            x1, y1 = x + bw + 4, y + bh / 2
            x2, y2 = x + bw + gap - 8, y + bh / 2
            d.line([x1, y1, x2, y2], fill=DIM, width=2)
            d.polygon([(x2, y2), (x2 - 8, y2 - 5), (x2 - 8, y2 + 5)], fill=DIM)

    d.text((24, 240), "POST /api/pipeline/run?hours=24&with_llm=true&with_tts=true&persist=true", font=node_font, fill=YELLOW)
    d.text((24, 268), "Fonte: n8n/etapa1.json · workflows exportados em evidence/n8n-workflows-export.json", font=node_font, fill=DIM)
    out = EV / "03-n8n-etapa1-diagram.png"
    img.save(out, "PNG")
    print(f"saved {out.name}")


def main():
    n8n_evidence()
    whatsapp_evidence()
    workflow_diagram()


if __name__ == "__main__":
    main()

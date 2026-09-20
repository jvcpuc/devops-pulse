# -*- coding: utf-8 -*-
"""Vídeo Etapa 3 — slides PDF + Edge TTS pt-BR Antonio (voz masculina neural)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "APRESENTACAO-DevOps-Pulse-AI.pdf"
PREVIEW = ROOT / "evidence" / "pdf-preview"
OUTDIR = ROOT / "video"
OUTDIR.mkdir(exist_ok=True)
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
VOICE = "pt-BR-AntonioNeural"
RATE = "-8%"  # um pouco mais lento = dicção técnica mais clara

SLIDES = [
    (1, "01-capitulo-problema"),
    (2, "02-diagnostico"),
    (4, "03-ambiente-docker"),
    (6, "04-n8n-etapa2"),
    (7, "05-prototipo-api"),
    (9, "06-sqlite-grid"),
    (11, "07-dashboard"),
    (13, "08-whatsapp"),
    (15, "09-performance-etica"),
    (16, "10-aprendizagem"),
]

# Termos técnicos escritos para pronúncia pt-BR convincente:
# n8n = ene-oito-ene · GitHub · Ollama · Kokoro · SQLite = sequelite
# pull requests = pul-riquéstes · LGPD · API · CI = integração contínua
SCRIPT = {
    "01-capitulo-problema": (
        "DevOps Pulse AI. Entrega final da AI Factory: validação, storytelling e impacto ético. "
        "Commits, pull-riquéstes, issues e integração contínua ficam espalhados no Guit-Hub. "
        "O time tem seis pessoas: cinco desenvolvedores, um tech lead e um product owner. "
        "O tech lead gasta cerca de vinte e cinco minutos por dia só para consolidar o boletim."
    ),
    "02-diagnostico": (
        "No diagnóstico, o processo manual era este: abrir o repositório, filtrar commits das últimas "
        "vinte e quatro horas, listar pull-riquéstes parados, checar integração contínua e issues, "
        "redigir o resumo e enviar no chat. O tech lead virava ponto único de consolidação. "
        "O product owner tinha visão reativa. "
        "A oportunidade: automatizar o ciclo input, process e output com API, inteligência local "
        "e entrega multicanal."
    ),
    "03-ambiente-docker": (
        "Ambiente validado na máquina local. No Dóquer rodam N-oito-N, Kokóro, "
        "Evolution API e Postgres. O modelo de linguagem local é o Olláma, com o llama três ponto dois. "
        "O health do microsserviço Python mostra quatro componentes no ar: Guit-Hub, Olláma, Kokóro "
        "e N-oito-N. Vinte e um testes automatizados passando. "
        "Modo demo desligado: os dados vêm do repositório real ene oito ene iô barra ene oito ene."
    ),
    "04-n8n-etapa2": (
        "A orquestração fica no N-oito-N. A etapa um dispara o pipeline do microsserviço. "
        "A etapa dois agenda a execução, valida o identificador de execução e distribui o boletim "
        "para WhatsApp, Telegram e e-mail. Se um canal falhar, o fluxo continua "
        "e a entrega não cai por inteiro. O Python calcula; a inteligência local interpreta; "
        "o N-oito-N coordena a entrega."
    ),
    "05-prototipo-api": (
        "O protótipo consome a API pública do Guit-Hub. Calcula métricas e alertas, "
        "gera resumo com Olláma e síntese de voz com Kokóro, e grava tudo no Sequelite. "
        "Execução de referência: status sucesso, fonte Guit-Hub. "
        "Coleta em cinco vírgula cinco segundos; modelo de linguagem em cinquenta e oito vírgula cinco; "
        "voz em dezoito vírgula seis. Total: oitenta e dois segundos e meio. "
        "Regra de ouro: o modelo interpreta indicadores já calculados. Ele não é a fonte primária."
    ),
    "06-sqlite-grid": (
        "Cada execução entra no Sequelite com um identificador rastreável. "
        "Para a apresentação, criamos um grid em HTML, sem abrir gerenciador de banco. "
        "Cada card mostra status, métricas e latência. "
        "O ponto central é o selo da fonte dos dados: Guit-Hub quando a coleta veio da API real, "
        "demo quando o pipeline foi testado sem token. "
        "Prova de funcionamento não se mistura com métrica de produção."
    ),
    "07-dashboard": (
        "O dashboard conta a história dos dados. Cards de commits, pull-riquéstes abertos, issues, "
        "execuções de integração contínua e taxa de sucesso. Alertas com severidade. Latência por etapa. "
        "E o antes e depois em números: de vinte e cinco minutos manuais para cerca de "
        "um minuto e quarenta de pipeline. Isso é aproximadamente noventa e quatro por cento "
        "menos tempo no ciclo. Com as premissas documentadas, oito horas e meia por mês "
        "liberadas do tech lead para mentoria e revisão — não para consolidação manual. "
        "Esse é o valor de negócio traduzido a partir do resultado técnico."
    ),
    "08-whatsapp": (
        "Entrega multicanal comprovada na prática. O boletim completo foi enviado ao grupo "
        "DevOps Pulse AI no WhatsApp, via Evolution API. "
        "Chegaram repositório, fonte, status, indicadores de vinte e quatro horas, "
        "alertas de integração contínua, pull-riquéstes parados, resultado do stress test e o pipeline. "
        "A instância devops-pulse está aberta, com WhatsApp pareado e pronto para envio."
    ),
    "09-performance-etica": (
        "Performance medida, sem achismo. Stress test de dez, vinte e cinquenta requisições: "
        "cem por cento de sucesso; p noventa e cinco em torno de sete segundos. "
        "Gargalos: API do Guit-Hub, Olláma e Kokóro. "
        "Melhorias priorizadas: cache da coleta, processamento assíncrono do resumo e da voz, "
        "Kokóro aquecido e histórico em planilha para o product owner. "
        "No plano ético e legal, LGPD aplicada de verdade: finalidade, minimização, transparência "
        "e segurança, com tokens fora do repositório. "
        "Inteligência artificial responsável: modelo local, prompt que proíbe inventar incidentes, "
        "fallback honesto e supervisão humana. "
        "Impacto social assumido em voz alta: métrica de repositório não pode virar ranking de pessoa. "
        "O valor é tempo e clareza para o time — não vigilância individual."
    ),
    "10-aprendizagem": (
        "Aprendizagem-chave da etapa final: traduzir resultado técnico em valor de negócio "
        "com responsabilidade social. Sistemas conectados por API, indicadores acionáveis, "
        "relatórios automatizados e limites éticos claros. "
        "Próximos passos: cache da coleta no Guit-Hub, processamento em paralelo, "
        "histórico em planilha e baseline de anomalias para reduzir alertas falsos. "
        "DevOps Pulse AI. Boletim inteligente de operações, com evidências reais "
        "e consciência dos impactos da inteligência artificial no trabalho de equipes de software."
    ),
}


def edge_tts(text: str, mp3: Path) -> None:
    cmd = [
        PY, "-m", "edge_tts",
        "--voice", VOICE,
        "--rate=-8%",
        "--text", text,
        "--write-media", str(mp3),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not mp3.exists() or mp3.stat().st_size < 2000:
        print(r.stderr[-600:] if r.stderr else r.stdout[-600:])
        raise RuntimeError("edge-tts failed " + mp3.name)


def ensure_slides() -> None:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    if len(list(PREVIEW.glob("APRESENTACAO-DevOps-Pulse-AI_*.png"))) < 16:
        subprocess.run(
            [sys.executable, "-m", "pypdfium2_cli", "render",
             str(PDF), "--output", str(PREVIEW), "--format", "png", "--scale", "1.5"],
            check=True, cwd=str(ROOT),
        )


def main() -> None:
    ensure_slides()
    segments = []
    total = 0.0
    for page, key in SLIDES:
        png = PREVIEW / f"APRESENTACAO-DevOps-Pulse-AI_{page:02d}.png"
        if not png.exists():
            cands = sorted(PREVIEW.glob(f"*_{page:02d}.png"))
            if not cands:
                print("missing slide", page)
                continue
            png = cands[-1]
        mp3 = OUTDIR / f"seg-{key}.mp3"
        wav = OUTDIR / f"seg-{key}-antonio.wav"
        print("TTS", key)
        edge_tts(SCRIPT[key], mp3)
        # convert to wav for stable concat/audio filter
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3), "-ar", "44100", "-ac", "2", str(wav)],
            check=True, capture_output=True,
        )
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(wav)],
            capture_output=True, text=True,
        )
        try:
            dur = float(probe.stdout.strip())
        except Exception:
            dur = 20.0
        dur = max(dur + 0.8, 5.0)
        total += dur
        out_seg = OUTDIR / f"seg-{key}.mp4"
        vf = (
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=0x0f1419"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-framerate", "30", "-i", str(png),
            "-i", str(wav),
            "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
            "-vf", vf,
            "-t", f"{dur:.2f}",
            "-movflags", "+faststart",
            str(out_seg),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-800:])
            raise RuntimeError("ffmpeg fail " + key)
        segments.append(out_seg)
        print(f"  {key}: {dur:.1f}s")

    print(f"total ~ {total/60:.2f} min ({total:.0f}s)")
    listfile = OUTDIR / "concat.txt"
    listfile.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
    final = OUTDIR / "DevOps-Pulse-Etapa3.mp4"
    for cmd in (
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c", "copy", "-movflags", "+faststart", str(final)],
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listfile),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(final)],
    ):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            break
    else:
        raise RuntimeError("concat failed")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(final)],
        capture_output=True, text=True,
    )
    print("VIDEO OK", final, "duration_s=", probe.stdout.strip(), "bytes=", final.stat().st_size)


if __name__ == "__main__":
    main()

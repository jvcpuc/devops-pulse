# -*- coding: utf-8 -*-
"""Gera vídeo da Etapa 3: slides do PDF + TTS pt-BR (SAPI Windows)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "APRESENTACAO-DevOps-Pulse-AI.pdf"
PREVIEW = ROOT / "evidence" / "pdf-preview"
OUTDIR = ROOT / "video"
OUTDIR.mkdir(exist_ok=True)

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

# Narração alvo ~6 min (faixa pedida: 5 a 8 minutos).
SCRIPT = [
    (
        "01-capitulo-problema",
        "DevOps Pulse AI. Entrega final da AI Factory: validação, storytelling e impacto ético. "
        "Commits, pull requests, issues e CI ficam espalhados no GitHub. "
        "No contexto analisado, a equipe tem seis pessoas: cinco devs, um tech lead e um PO. "
        "O tech lead gasta cerca de vinte e cinco minutos por dia só para consolidar o boletim operacional.",
    ),
    (
        "02-diagnostico",
        "O diagnóstico documentou o processo manual: abrir o repositório, filtrar commits de 24 horas, "
        "listar PRs parados, checar CI e issues, redigir resumo e enviar no chat. "
        "O TL vira ponto único de consolidação; o PO tem visão reativa; os devs dependem de alguém notar o risco. "
        "A oportunidade é formalizar input, process e output com API, IA local e entrega multicanal.",
    ),
    (
        "03-ambiente-docker",
        "Ambiente validado localmente: Docker com n8n, Kokoro, Evolution API e Postgres. "
        "Ollama com llama3.2. O health do microsserviço mostra quatro componentes no ar "
        "e demo mode desligado — dados reais do repositório n8n-io barra n8n. "
        "Vinte e um testes automatizados passando.",
    ),
    (
        "04-n8n-etapa2",
        "A orquestração fica no n8n: a Etapa um dispara o pipeline; a Etapa dois agenda, valida execution_id "
        "e distribui para WhatsApp, Telegram e e-mail, com continuidade se um canal falhar. "
        "Python calcula; a IA local interpreta; o n8n coordena a entrega.",
    ),
    (
        "05-prototipo-api",
        "O protótipo consome a API do GitHub, calcula métricas e alertas, gera resumo com Ollama "
        "e áudio com Kokoro, gravando tudo em SQLite. "
        "Execução de referência PULSE-20260917-121306-7999: status success, fonte github, "
        "coleta 5,5 s, LLM 58,5 s, TTS 18,6 s, total 82,5 segundos. "
        "O LLM interpreta indicadores já calculados — não é fonte primária.",
    ),
    (
        "06-sqlite-grid",
        "Cada execução entra no SQLite com execution_id rastreável. "
        "Criamos um grid HTML para a apresentação, sem abrir SGDB. "
        "O badge da fonte distingue github de demo: prova de pipeline não vira métrica de produção.",
    ),
    (
        "07-dashboard",
        "O dashboard conta a história dos dados: cards de commits, PRs, issues e CI, "
        "alertas de severidade, latência por etapa e antes versus depois. "
        "De 25 minutos manuais para cerca de 1,4 minuto de pipeline — aproximadamente 94% menos tempo, "
        "equivalente a 8,5 horas por mês liberadas do TL, segundo as premissas documentadas.",
    ),
    (
        "08-whatsapp",
        "Entrega multicanal comprovada: o boletim completo chegou ao grupo DevOps Pulse AI "
        "via Evolution API, com indicadores, alertas, stress test e pipeline. "
        "A instância devops-pulse está com connection state open, WhatsApp pareado.",
    ),
    (
        "09-performance-etica",
        "Performance medida: stress 10/25/50 com 100% de sucesso; p95 em torno de 7 segundos. "
        "Gargalos: GitHub API, Ollama e Kokoro. Melhorias priorizadas: cache da coleta, "
        "LLM assíncrono, TTS estável e Sheets no n8n. "
        "LGPD e IA responsável: minimização, tokens fora do Git, LLM local, fallback honesto e supervisão humana. "
        "Impacto social assumido: métrica de repositório não vira ranking de pessoa.",
    ),
    (
        "10-aprendizagem",
        "Aprendizagem-chave: traduzir resultado técnico em valor de negócio com responsabilidade social. "
        "Sistemas conectados por API, indicadores acionáveis, automatização de relatórios e limites éticos claros. "
        "Próximos passos: cache, paralelismo, Sheets e baseline de anomalias. "
        "DevOps Pulse AI — boletim inteligente de operações com evidências reais.",
    ),
]


def say(text: str, wav: Path) -> None:
    """Portuguese TTS via Windows SAPI."""
    ps = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$pt = $s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Culture.Name -like 'pt*' }} | Select-Object -First 1
if ($pt) {{ $s.SelectVoice($pt.VoiceInfo.Name) }}
$s.Rate = 0
$s.SetOutputToWaveFile('{wav}')
$s.Speak('{text.replace("'", "''")}')
$s.Dispose()
"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0 or not wav.exists() or wav.stat().st_size < 1000:
        print("SAPI failed:", (r.stderr or r.stdout or "")[-500:])
        raise RuntimeError(f"TTS failed for {wav.name}")


def ensure_slides() -> None:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    existing = list(PREVIEW.glob("APRESENTACAO-DevOps-Pulse-AI_*.png"))
    if len(existing) < 16:
        cmd = [
            sys.executable, "-m", "pypdfium2_cli", "render",
            str(PDF), "--output", str(PREVIEW), "--format", "png", "--scale", "1.5",
        ]
        subprocess.run(cmd, check=True, cwd=str(ROOT))


def main() -> None:
    ensure_slides()
    segments = []
    total = 0.0
    for page, key in SLIDES:
        png = PREVIEW / f"APRESENTACAO-DevOps-Pulse-AI_{page:02d}.png"
        if not png.exists():
            cands = sorted(PREVIEW.glob(f"*_{page:02d}.png"))
            if not cands:
                print("missing slide page", page)
                continue
            png = cands[-1]
        wav = OUTDIR / f"seg-{key}.wav"
        text = dict(SCRIPT)[key]
        print("TTS", key)
        say(text, wav)
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", str(wav)],
            capture_output=True, text=True,
        )
        try:
            dur = float(probe.stdout.strip())
        except Exception:
            dur = 10.0
        dur = max(dur + 0.6, 4.0)
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
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
            "-vf", vf,
            "-t", f"{dur:.2f}",
            "-movflags", "+faststart",
            str(out_seg),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-800:])
            raise RuntimeError("ffmpeg seg failed " + key)
        segments.append(out_seg)
        print(f"  {key}: {dur:.1f}s -> {out_seg.name}")

    print(f"total narrado ~ {total/60:.2f} min ({total:.0f}s)")
    listfile = OUTDIR / "concat.txt"
    listfile.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in segments),
        encoding="utf-8",
    )
    final = OUTDIR / "DevOps-Pulse-Etapa3.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(listfile), "-c", "copy",
        "-movflags", "+faststart",
        str(final),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(listfile),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart",
            str(final),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-800:])
            raise RuntimeError("concat failed")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(final)],
        capture_output=True, text=True,
    )
    print("VIDEO OK", final, "duration_s=", probe.stdout.strip(), "bytes=", final.stat().st_size)


if __name__ == "__main__":
    main()

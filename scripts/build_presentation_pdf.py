# -*- coding: utf-8 -*-
"""Gera o PDF da apresentacao DevOps Pulse AI (AI Factory / PUC)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
OUT = ROOT / "APRESENTACAO-DevOps-Pulse-AI.pdf"

INK = colors.HexColor("#0f1419")
PANEL = colors.HexColor("#1a2332")
ACCENT = colors.HexColor("#3d9cf0")
MUTED = colors.HexColor("#5b6b82")
BORDER = colors.HexColor("#c5cedb")
LIGHT_BG = colors.HexColor("#f4f7fb")
WHITE = colors.white

FONT = "Arial"
FONT_B = "Arial-Bold"


def register_fonts() -> None:
    candidates = [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
        (r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\tahomabd.ttf"),
    ]
    for regular, bold in candidates:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont(FONT, regular))
            pdfmetrics.registerFont(TTFont(FONT_B, bold))
            return
    raise RuntimeError("Nenhuma fonte TTF adequada encontrada em C:\\Windows\\Fonts")


def styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(
        "CoverTitle", fontName=FONT_B, fontSize=26, leading=32,
        textColor=INK, alignment=TA_LEFT, spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        "CoverSub", fontName=FONT, fontSize=12, leading=16,
        textColor=MUTED, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        "H1", fontName=FONT_B, fontSize=15, leading=19,
        textColor=INK, spaceBefore=10, spaceAfter=8,
    ))
    ss.add(ParagraphStyle(
        "H2", fontName=FONT_B, fontSize=11, leading=14,
        textColor=ACCENT, spaceBefore=8, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        "Body", fontName=FONT, fontSize=9.5, leading=13,
        textColor=INK, spaceAfter=4,
    ))
    ss.add(ParagraphStyle(
        "Small", fontName=FONT, fontSize=8, leading=11,
        textColor=MUTED, spaceAfter=3,
    ))
    ss.add(ParagraphStyle(
        "BulletItem", fontName=FONT, fontSize=9.5, leading=13,
        textColor=INK, leftIndent=8, spaceAfter=2,
    ))
    ss.add(ParagraphStyle(
        "Caption", fontName=FONT, fontSize=8, leading=10,
        textColor=MUTED, alignment=TA_CENTER, spaceBefore=2, spaceAfter=10,
    ))
    ss.add(ParagraphStyle(
        "CodeBlock", fontName=FONT, fontSize=8, leading=11,
        textColor=INK, backColor=LIGHT_BG, borderPadding=5,
        spaceBefore=4, spaceAfter=6,
    ))
    ss.add(ParagraphStyle(
        "KPILabel", fontName=FONT, fontSize=7.5, leading=9,
        textColor=MUTED, alignment=TA_CENTER,
    ))
    ss.add(ParagraphStyle(
        "KPIValue", fontName=FONT_B, fontSize=12, leading=14,
        textColor=INK, alignment=TA_CENTER,
    ))
    return ss


def img(path: Path, max_w_mm: float = 170, max_h_mm: float = 110):
    if not path.exists():
        return Paragraph("[imagem ausente: %s]" % path.name, styles()["Small"])
    with PILImage.open(path) as im:
        w, h = im.size
    max_w = max_w_mm * mm
    max_h = max_h_mm * mm
    scale = min(max_w / w, max_h / h, 1.0)
    return Image(str(path), width=w * scale, height=h * scale, kind="proportional")


def term_img(path: Path, max_h_mm: float = 90):
    """Terminal/UI evidence: always use full page width for readability."""
    return img(path, max_w_mm=174, max_h_mm=max_h_mm)


def caption(text: str, S):
    return Paragraph(text, S["Caption"])


def section_table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    bg0 = PANEL if header else LIGHT_BG
    tc0 = WHITE if header else INK
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), bg0),
        ("TEXTCOLOR", (0, 0), (-1, 0), tc0),
        ("FONTNAME", (0, 0), (-1, 0), FONT_B),
        ("FONTNAME", (0, 1), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
    ]))
    return t


def kpi_row(items, S):
    cells = []
    for label, value in items:
        inner = Table(
            [[Paragraph(label, S["KPILabel"])], [Paragraph(str(value), S["KPIValue"])]],
            colWidths=[38 * mm],
        )
        inner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        cells.append(inner)
    t = Table([cells], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def bullets(items, S):
    return ListFlowable(
        [ListItem(Paragraph(x, S["BulletItem"]), leftIndent=10) for x in items],
        bulletType="bullet",
        start="circle",
        leftIndent=12,
    )


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8 * mm, "DevOps Pulse AI · AI Factory · uso acadêmico")
    canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, "pág. %d" % doc.page)
    canvas.restoreState()


def build():
    register_fonts()
    S = styles()
    story = []

    # CAPA
    story.append(Spacer(1, 18 * mm))
    story.append(Paragraph("DevOps Pulse AI", S["CoverTitle"]))
    story.append(Paragraph(
        "Boletim inteligente de operações de desenvolvimento", S["CoverSub"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT, spaceBefore=6, spaceAfter=10))
    story.append(Paragraph(
        "Projeto acadêmico <b>AI Factory</b> — Etapa 1 / Unidade 2<br/>"
        "Pipeline de automação: GitHub API → Python/FastAPI → Ollama → Kokoro TTS → SQLite → n8n → WhatsApp",
        S["Body"],
    ))
    story.append(Spacer(1, 6 * mm))
    story.append(kpi_row([
        ("Testes", "21/21"),
        ("Repo monitorado", "n8n-io/n8n"),
        ("Fonte de dados", "GitHub real"),
        ("Pipeline medido", "~83 s"),
    ], S))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "<b>Itens cobertos (especificação da etapa)</b><br/>"
        "ID 1.1 Diagnóstico · ID 2 Canvas (objetivos, entregáveis, papéis) · "
        "ID 2.1 Ambiente de automação · ID 2.2 Protótipo funcional · "
        "Aprendizagem-chave: input → process → output",
        S["Body"],
    ))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "Equipe de contexto: 5 devs (1 TL) + 1 PO · Persistência: SQLite · LLM local: Ollama · TTS: Kokoro",
        S["Small"],
    ))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        "Documento gerado em 17/09/2026 com evidências reais capturadas no ambiente local.",
        S["Small"],
    ))
    story.append(PageBreak())

    # 1 DIAGNOSTICO
    story.append(Paragraph("1. Diagnóstico do desafio real (ID 1.1)", S["H1"]))
    story.append(Paragraph(
        "Squad de <b>6 pessoas</b> (5 desenvolvedores — sendo 1 Tech Lead — e 1 Product Owner) depende do GitHub "
        "para commits, pull requests, issues e CI. A informação fica <b>espalhada em telas diferentes</b> e a "
        "consolidação do boletim operacional é manual.",
        S["Body"],
    ))
    story.append(Paragraph("Processo manual observado", S["H2"]))
    story.append(bullets([
        "Abrir o repositório e filtrar commits das últimas 24 h",
        "Listar PRs abertos e marcar os stale",
        "Checar issues e taxa de sucesso de Actions/CI",
        "Redigir resumo e enviar no chat/e-mail do time",
    ], S))
    story.append(Paragraph("Impacto e tempo", S["H2"]))
    story.append(section_table([
        ["Atividade", "Tempo", "Quem"],
        ["Consolidar boletim manual (UI GitHub → resumo → envio)", "~25 min/dia (premissa)", "TL"],
        ["Supervisão da automação (dashboard + alertas)", "~2 min/dia", "TL / PO"],
        ["Economia estimada", "≈ 8,5 h/mês do TL", "—"],
    ], col_widths=[95 * mm, 40 * mm, 30 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Oportunidade de automação", S["H2"]))
    story.append(Paragraph(
        "Ciclo formalizável: <b>INPUT</b> GitHub API → <b>PROCESS</b> métricas + alertas + LLM (Ollama) + áudio (Kokoro) → "
        "<b>OUTPUT</b> JSON, SQLite com execution_id, n8n e WhatsApp.",
        S["Body"],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Fontes espalhadas no GitHub (evidência do problema)", S["H2"]))
    story.append(img(EV / "13-github.png", 170, 70))
    story.append(caption("Fig. 1 — Repositório monitorado (n8n-io/n8n): commits/PRs/issues/CI em telas separadas.", S))
    story.append(PageBreak())

    # 2 CANVAS
    story.append(Paragraph("2. Canvas do projeto — objetivos, entregáveis e papéis (ID 2)", S["H1"]))
    story.append(section_table([
        ["Campo", "Conteúdo"],
        ["Problema", "Informações de desenvolvimento espalhadas; consolidação manual atrasa decisões."],
        ["Público", "Tech leads, PO e equipes de software."],
        ["Objetivo", "Boletim operacional automatizado com indicadores, alertas e resumo executivo."],
        ["Proposta de valor", "Menos esforço manual, rastreabilidade por execution_id, IA local, entrega em WhatsApp."],
        ["Entradas", "GitHub API (commits, issues, PRs, workflow runs)."],
        ["Processamento", "Python: normalizar → métricas → alertas → Ollama → Kokoro → SQLite."],
        ["Saídas", "JSON /api/pulse, resumo em texto, áudio .wav, SQLite, notificações, dashboard."],
        ["Recursos / stack", "Python 3.12, FastAPI, n8n, Ollama, Kokoro, SQLite, Evolution API, Docker."],
        ["Riscos", "API indisponível, rate limit, Ollama lento, TTS fora, alucinação, vazamento de token."],
        ["Mitigações", "Retry, demo mode rotulado, fallback texto, .env gitignored, prompt restritivo, supervisão."],
        ["Entregáveis", "Microsserviço, workflows n8n, 21 testes, stress test, dashboard, docs, evidências, PDF."],
    ], col_widths=[35 * mm, 135 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Papéis da equipe (6 pessoas)", S["H2"]))
    story.append(section_table([
        ["Papel", "Qtd", "Responsabilidade"],
        ["Tech Lead (1 dos 5 devs)", "1", "Dono do boletim, risco de CI/PR e revisão técnica."],
        ["Desenvolvedores", "4", "Implementação, testes, integrações e consumo do status."],
        ["Product Owner", "1", "Prioridade, requisitos, aceite e visão de valor/ROI."],
    ], col_widths=[50 * mm, 15 * mm, 105 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Objetivos SMART (resumo)", S["H2"]))
    story.append(bullets([
        "O1 Coleta de API pública · O2 Indicadores · O3 Resumo Ollama · O4 Áudio Kokoro · O5 Orquestração n8n",
        "O6 Persistência SQLite · O7 Multicanal · O8 Robustez (retries/logs/fallbacks) · O9 Performance · O10 Avaliação",
    ], S))
    story.append(PageBreak())

    # 3 AMBIENTE
    story.append(Paragraph("3. Ambiente de automação (ID 2.1)", S["H1"]))
    story.append(Paragraph(
        "Chamadas HTTP em Python (FastAPI + curl), fluxos no n8n e Ollama/Kokoro executando localmente.",
        S["Body"],
    ))
    story.append(Paragraph("Saúde do sistema (componentes reais)", S["H2"]))
    story.append(term_img(EV / "02-python.png", 75))
    story.append(caption("Fig. 2 — /health: GitHub, Ollama, Kokoro e n8n OK · demo_mode=false.", S))
    story.append(Paragraph("Infra local — Docker Desktop (containers no ar)", S["H2"]))
    story.append(term_img(EV / "n8n_1.png", 90))
    story.append(caption(
        "Fig. 3 — Docker Desktop: n8n (:5678), kokoro (:8880), evo-postgres (:5433) e evolution-api (:8080) em execução.",
        S,
    ))
    story.append(PageBreak())
    story.append(Paragraph("LLM local — Ollama · TTS local — Kokoro", S["H2"]))
    story.append(term_img(EV / "04-ollama.png", 55))
    story.append(caption("Fig. 4 — Modelo llama3.2:1b no Ollama local.", S))
    story.append(term_img(EV / "05-kokoro.png", 45))
    story.append(caption("Fig. 5 — Áudios .wav gerados pelo Kokoro (voz pf_dora).", S))
    story.append(PageBreak())

    story.append(Paragraph("3.1 n8n — workflows no editor", S["H2"]))
    story.append(Paragraph(
        "Workflows importados e prontos para execução (UI do n8n). "
        "Etapa 1 orquestra o microsserviço; Etapa 2 entrega em WhatsApp/Telegram/e-mail.",
        S["Body"],
    ))
    story.append(term_img(EV / "n8n.png", 95))
    story.append(caption(
        "Fig. 6 — n8n UI · Etapa 2 (Evolution WhatsApp + Telegram): "
        "Schedule → Microsserviço → Preparar texto → WhatsApp/Telegram → Log final.",
        S,
    ))
    story.append(PageBreak())
    story.append(term_img(EV / "n8n_2.png", 95))
    story.append(caption(
        "Fig. 7 — n8n UI · Etapa 2 (Multicanal): "
        "Schedule → Microsserviço → Validação → E-mail/WhatsApp → Log final.",
        S,
    ))
    story.append(term_img(EV / "03-n8n-etapa1-diagram.png", 45))
    story.append(caption("Fig. 8 — Diagrama da Etapa 1: Manual Trigger → HTTP pipeline → IF success.", S))
    story.append(term_img(EV / "03-n8n-etapa1.png", 70))
    story.append(caption("Fig. 9 — Workflows DevOps Pulse listados no n8n (CLI + API).", S))
    story.append(PageBreak())

    # 4 PROTOTIPO
    story.append(Paragraph("4. Protótipo funcional (ID 2.2)", S["H1"]))
    story.append(Paragraph(
        "Consome <b>API pública real</b> (GitHub), gera <b>resumo LLM</b> (Ollama), sintetiza <b>áudio TTS</b> (Kokoro) "
        "e grava o resultado em <b>banco simples</b> (SQLite) com rastreio por execution_id.",
        S["Body"],
    ))
    story.append(Paragraph(
        "POST /api/pipeline/run?hours=24&amp;with_llm=true&amp;with_tts=true&amp;persist=true",
        S["CodeBlock"],
    ))
    story.append(Paragraph("Execução de referência", S["H2"]))
    story.append(section_table([
        ["Campo", "Valor"],
        ["execution_id", "PULSE-20260917-121306-7999"],
        ["Status / fonte", "success / github (n8n-io/n8n)"],
        ["Latência total", "82 549 ms (coleta 5,5 s · LLM 58,5 s · TTS 18,6 s · persist 11 ms)"],
        ["Saídas", "JSON + summary + audio .wav + linha SQLite"],
    ], col_widths=[40 * mm, 130 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("API /api/pulse — métricas reais (terminal)", S["H2"]))
    story.append(term_img(EV / "01-api-text.png", 95))
    story.append(caption("Fig. 10 — Payload com metrics, alerts, timings e data_source=github.", S))
    story.append(PageBreak())
    story.append(Paragraph("Logs estruturados do pipeline", S["H2"]))
    story.append(term_img(EV / "12-logs.png", 120))
    story.append(caption("Fig. 11 — logs/app.log com etapas e execution_id.", S))
    story.append(PageBreak())

    story.append(Paragraph("4.1 Persistência — SQLite (grid para apresentação)", S["H2"]))
    story.append(Paragraph(
        "No lugar de abrir um SGDB, a página dashboard/sqlite.html exibe o histórico "
        "com badge da <b>fonte dos dados</b> (github vs demo).",
        S["Body"],
    ))
    story.append(img(EV / "06b-sqlite-grid.png", 174, 125))
    story.append(caption("Fig. 12 — Grid de execuções do SQLite com fonte, status, métricas e latência.", S))
    story.append(term_img(EV / "06-planilha.png", 60))
    story.append(caption("Fig. 13 — Tabela executions no banco pulse.db.", S))
    story.append(PageBreak())

    story.append(Paragraph("4.2 Dashboard executivo", S["H2"]))
    story.append(img(EV / "10-dashboard.png", 174, 115))
    story.append(caption("Fig. 14 — Cards, alertas, latências por etapa e antes × depois.", S))
    story.append(PageBreak())
    story.append(Paragraph("4.3 Robustez — testes e stress", S["H2"]))
    story.append(term_img(EV / "02b-pytest.png", 85))
    story.append(caption("Fig. 15 — pytest: 21 passed.", S))
    story.append(term_img(EV / "11-stress-test.png", 50))
    story.append(caption("Fig. 16 — Stress test /api/pulse (10/25/50 req, 100% sucesso).", S))
    story.append(PageBreak())

    # 5 WHATSAPP
    story.append(Paragraph("5. Entrega multicanal — WhatsApp (n8n + Evolution API)", S["H1"]))
    story.append(Paragraph(
        "Boletim completo enviado ao grupo <b>DevOps Pulse AI</b> no formato consolidado "
        "(indicadores + alertas + stress + pipeline).",
        S["Body"],
    ))
    try:
        boletim = (EV / "whatsapp-boletim.txt").read_text(encoding="utf-8")
    except Exception:
        boletim = "(whatsapp-boletim.txt ausente)"
    story.append(Paragraph(boletim.replace("\n", "<br/>"), S["CodeBlock"]))
    story.append(Paragraph("Comprovação de entrega no WhatsApp (grupo DevOps Pulse AI)", S["H2"]))
    story.append(img(EV / "whatsapp.png", 168, 125))
    story.append(caption(
        "Fig. 17 — Conversa WhatsApp: boletim completo PULSE-20260917-124330-A359 "
        "(repo n8n-io/n8n · fonte github · CI 63% · alertas + stress + pipeline).",
        S,
    ))
    story.append(term_img(EV / "09-whatsapp.png", 70))
    story.append(caption("Fig. 18 — Comprovante de envio via Evolution API (key + remoteJid do grupo).", S))
    story.append(term_img(EV / "07-evolution-manager.png", 80))
    story.append(caption("Fig. 19 — Evolution API / instância devops-pulse (connectionState=open · WhatsApp pareado).", S))
    story.append(PageBreak())

    # 6 PERFORMANCE
    story.append(Paragraph("6. Performance e responsabilidade (LGPD / IA)", S["H1"]))
    story.append(section_table([
        ["Cenário", "Tempo", "Origem"],
        ["Manual (premissa)", "25 min", "Consolidar GitHub UI + resumo + envio"],
        ["Automatizado (medido)", "82,5 s", "PULSE-20260917-121306-7999"],
        ["Redução", "~94% no ciclo completo", "(25 − 1,4) / 25 com pipeline de ~1,4 min"],
    ], col_widths=[50 * mm, 40 * mm, 80 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Princípios aplicados", S["H2"]))
    story.append(bullets([
        "O LLM <b>não é fonte primária</b> — só interpreta métricas já calculadas (reduz alucinação).",
        "Minimização: Ollama recebe apenas métricas + alertas.",
        "Tokens e chaves só em .env / pulse.env (gitignored).",
        "Modo demo rotulado — nunca apresentar demo como produção.",
        "Fallbacks explícitos: LLM_ERROR, TTS_ERROR, PERSISTENCE_ERROR, onError continue no n8n.",
    ], S))
    story.append(PageBreak())

    # 7 APRENDIZAGEM
    story.append(Paragraph("7. Aprendizagem-chave — input → process → output", S["H1"]))
    story.append(section_table([
        ["Etapa", "O que acontece", "Tecnologia"],
        ["INPUT", "Coleta de commits, PRs, issues e workflow runs", "GitHub API + httpx + retry"],
        ["PROCESS", "Métricas, alertas, resumo em linguagem natural, síntese de voz", "Python, Ollama, Kokoro"],
        ["OUTPUT", "JSON, áudio, SQLite, dashboard e notificação", "FastAPI, SQLite, n8n, Evolution"],
    ], col_widths=[30 * mm, 85 * mm, 55 * mm]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "O protótipo demonstra que é possível <b>conectar sistemas via API</b>, transformar dados em indicadores "
        "acionáveis e automatizar a comunicação operacional — o primeiro passo da transformação digital do desafio real.",
        S["Body"],
    ))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Como demonstrar ao vivo (roteiro curto)", S["H2"]))
    story.append(bullets([
        "curl /health → componentes no ar (demo_mode=false)",
        "curl /api/pulse → métricas reais do n8n-io/n8n",
        "POST /api/pipeline/run → logs + áudio + SQLite",
        "Abrir dashboard/sqlite.html → grid com fonte github",
        "Mostrar WhatsApp do grupo com o boletim completo",
    ], S))
    story.append(PageBreak())

    # 8 ANEXOS
    story.append(Paragraph("8. Anexos — evidências adicionais", S["H1"]))
    extras = [
        ("13-github-actions.png", "Actions/CI do repositório monitorado", 70),
        ("13-github-pulls.png", "Pull requests abertos (fila manual hoje)", 70),
        ("01-api-health.png", "GET /health — componentes do sistema (terminal)", 80),
        ("n8n_3.png", "n8n UI — workflow de teste FastAPI (Webhook → HTTP Request)", 80),
        ("03-n8n-login.png", "UI do n8n protegida (login do owner)", 50),
        ("08-email.png", "Canal de e-mail (reserva) documentado", 40),
    ]
    for name, title, h in extras:
        p = EV / name
        if p.exists():
            story.append(Paragraph(title, S["H2"]))
            if name.startswith("n8n_") or "api-health" in name or name.startswith("0"):
                story.append(term_img(p, h))
            else:
                story.append(img(p, 170, h))
            story.append(caption("Fig. anexa — %s" % name, S))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        "Arquivos do projeto: C:\\PUC\\2_Semestre\\AIFactory\\devops-pulse<br/>"
        "Documentação: README.md · ARCHITECTURE.md · docs/diagnostico.md · docs/canvas.md · ETHICS-LGPD.md · PERFORMANCE.md",
        S["Small"],
    ))

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="DevOps Pulse AI — Apresentação AI Factory",
        author="DevOps Pulse AI",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("PDF gerado: %s (%d bytes)" % (OUT, OUT.stat().st_size))


if __name__ == "__main__":
    build()

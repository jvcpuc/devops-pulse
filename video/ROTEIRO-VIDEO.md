# Roteiro do vídeo — Etapa 3 (5–8 min)

> Objetivo: dominar técnica → valor de negócio → responsabilidade social.
> Duração alvo: **~6 min**. Use o PDF `APRESENTACAO-DevOps-Pulse-AI.pdf` ou a demo ao vivo.

## Pré (30 s antes)

- API no ar com `demo_mode: false` (`/health`)
- Abas: health · `/api/pulse` · dashboard · sqlite.html · n8n · WhatsApp grupo
- PDF aberto na seção de métricas/ética
- Áudio já gerado: `data/results/audio/PULSE-20260917-121306-7999.wav`

## Script bloco a bloco

### 0:00–0:40 — Problema (storytelling)
**Diga:** “Num squad de 6 pessoas — 5 devs, 1 TL e 1 PO — commits, PRs, issues e CI ficam espalhados no GitHub. O TL gasta cerca de 25 minutos por dia consolidando um boletim manual. O PO só descobre atraso quando alguém comenta no chat.”
**Mostre:** print do GitHub (PRs/Actions) ou Fig. 1 do PDF.
**Peso da rubrica:** narrativa + objetivo.

### 0:40–1:20 — Solução e arquitetura
**Diga:** “Construímos um pipeline de automação com IA local: GitHub API → Python/FastAPI → métricas e alertas → Ollama (resumo) → Kokoro (áudio) → SQLite → n8n → WhatsApp do grupo.”
**Mostre:** diagrama do PDF / `ARCHITECTURE.md`.
**Aponte:** “O LLM **não** inventa número — só interpreta indicadores já calculados.”

### 1:20–2:20 — Ambiente validado (ID 2.1 / evidências)
**Diga:** “Ambiente local comprovado: Ollama llama3.2:1b, Kokoro, n8n e Evolution API no Docker. Testes 21 de 21. Demo mode desligado — dados reais do repositório n8n-io/n8n.”
**Mostre:** `/health`, Docker Desktop, pytest.

### 2:20–3:40 — Protótipo e resultado medido (ID 2.2 / métricas)
**Diga:** “Execução de referência PULSE-20260917-121306-7999: status success, fonte github. Coleta 5,5 s, Ollama 58,5 s, Kokoro 18,6 s — total 82,5 segundos. Stress de 10 a 50 requisições: 100% de sucesso, p95 em torno de 7 segundos.”
**Mostre:** JSON `/api/pulse`, logs, áudio `.wav`, grid SQLite, WhatsApp com o boletim completo.
**Número de impacto:** “De 25 minutos manuais para ~1,4 minuto — cerca de 94% menos tempo; ~8,5 horas/mês liberadas do TL.”

### 3:40–4:40 — Storytelling com dados (ID 3.1)
**Diga:** “O dashboard conta a história: cards de commits/PRs/CI, alertas de severidade, latência por etapa e comparação antes × depois. O grid do SQLite mostra a **fonte** de cada execução — badge github vs demo — para não misturar prova de pipeline com métrica de produção.”
**Mostre:** `dashboard/index.html` e `dashboard/sqlite.html`.
**Aponte:** 3 alertas do dia (CI baixa, PR stale, issues).

### 4:40–5:30 — Melhorias (análise crítica)
**Diga:** “Os gargalos estão medidos: GitHub API, Ollama e Kokoro. Prioridade de melhoria: cache da coleta (M1), LLM assíncrono (M2), TTS estável (M3), Sheets no n8n para o PO (M5) e baseline de anomalias (M6).”
**Mostre:** tabela M1–M8 em `PERFORMANCE.md`.

### 5:30–6:20 — Ética, LGPD e valor social (ID 3.2)
**Diga:** “Impacto ético: minimização de dados, LLM local (nada sai da máquina), tokens fora do Git e demo rotulado. Risco social que assumimos: métrica de commits **não** pode virar ranking de pessoa — o boletim é agregado do repositório e exige supervisão humana. Valor: menos consolidação manual, mais tempo de mentoria e decisão com dados.”
**Mostre:** `ETHICS-LGPD.md` (princípios LGPD + tabela de riscos/mitigações).

### 6:20–6:40 — Fechamento
**Diga:** “Aprendizagem-chave: conectar sistemas via API, transformar dados em indicadores acionáveis e traduzir resultado técnico em valor de negócio — com responsabilidade social. Próximos passos: cache, paralelismo e histórico em Sheets.”

## Checklist de avaliação (autoavaliação)

- [ ] Citou números medidos (latência, 100% stress, 94%, 8,5 h/mês)
- [ ] Mostrou evidência (print/dashboard/WhatsApp) — não só “falou”
- [ ] Nomeou gargalos e ao menos 2 melhorias
- [ ] Explicou LGPD + 1 risco social + mitigação
- [ ] Disse que demo ≠ produção quando relevante
- [ ] Ficou entre 5 e 8 minutos

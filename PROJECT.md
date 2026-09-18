# PROJECT.md — resumo executivo

Projeto acadêmico **AI Factory**: **DevOps Pulse AI — Boletim Inteligente de Operações**.

## Objetivos SMART (enxutos)

| ID | Objetivo | Critério de sucesso |
|----|----------|---------------------|
| O1 | Coletar dados de API pública | `/api/pulse` retorna JSON com métricas |
| O2 | Transformar em indicadores | `metrics.py` + testes verdes |
| O3 | Resumo via Ollama | campo `summary` (ou fallback rotulado) |
| O4 | Áudio via Kokoro | arquivo `.wav` ou `TTS_ERROR` explícito |
| O5 | Orquestrar no n8n | workflows Etapa 1 e 2 importáveis |
| O6 | Persistir execuções | SQLite com `execution_id` |
| O7 | Multicanal | e-mail + WhatsApp no n8n |
| O8 | Robustez | retries, logs, `.env`, fallbacks |
| O9 | Performance | stress test + relatório real |
| O10 | Avaliação | dashboard, LGPD, ROI documentado |

## Prioridade

```text
FUNCIONAR → MEDIR → DOCUMENTAR → EXPLICAR
```

## Arquivos-chave

- Código: `app/`
- Testes: `tests/`
- n8n: `n8n/`
- Ética: `ETHICS-LGPD.md`
- Performance/ROI/melhorias: `PERFORMANCE.md`
- Etapa 3 (mapa + storytelling): `ETAPA3.md`
- Vídeo/roteiro: `video/ROTEIRO-VIDEO.md` · `video/DevOps-Pulse-Etapa3.mp4`
- Apresentação/PDF: `APRESENTACAO-DevOps-Pulse-AI.pdf`


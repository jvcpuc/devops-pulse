# Etapa 3 — Validação, storytelling e impacto ético

> Mapeamento da **rubrica** para evidências do projeto DevOps Pulse AI.

## 1. Mapa requisito → evidência

| Item da Etapa 3 | Onde está | Status |
|-----------------|-----------|--------|
| **ID 3.1** Dashboard/infográfico com storytelling | `dashboard/index.html` · `dashboard/sqlite.html` · PDF §§4.1–4.2 · PERFORMANCE “Impacto qualitativo” | OK |
| **ID 3.2** Impacto ético/legal/social + LGPD + IA responsável | `ETHICS-LGPD.md` (princípios art. 6º, riscos sociais, mitigações, checklist) · PDF §6 | OK |
| **Métricas** latência, taxa de sucesso, ROI | `PERFORMANCE.md` · stress JSON · SQLite · PDF §6 | OK |
| **Análise + propostas de melhoria** | `PERFORMANCE.md` M1–M8 com prioridade | OK |
| **Documentação das etapas do pipeline** | `ARCHITECTURE.md` · `README.md` · `docs/requisitos.md` · PDF §§3–4 | OK |
| **Vídeo 5–8 min com narrativa e dados** | `video/DevOps-Pulse-Etapa3.mp4` + roteiro `video/ROTEIRO-VIDEO.md` | Gerar |
| **Aprendizagem-chave** (resultado técnico → valor de negócio + responsabilidade) | PDF §7 · ETHICS §5 · PERFORMANCE impacto qualitativo | OK |

## 2. Critérios da rubrica (como pontuar alto)

| Critério | Peso | O que o avaliador procura | Como respondemos |
|----------|------|---------------------------|------------------|
| Apresentação clara + storytelling | 30% | Narrativa coerente, visual eficiente, ligação com o objetivo | Story “problema → pipeline → números → valor”; dashboard com antes×depois; grid SQLite com fonte github/demo |
| Impacto ético/legal/social LGPD + IA resp. | 25% | Profundidade, riscos, mitigações, social | Tabela LGPD art. 6º; riscos (vigilância, volume, WhatsApp) + mitigações; checklist do operador |
| Documentação + métricas + vídeo 5–10 min | 45% | Latência, sucesso, ROI, melhorias, vídeo estruturado | PERFORMANCE medido + M1–M8; vídeo com evidências quantitativas |

## 3. Storytelling (data story) — 8 blocos

1. **Gatilho:** boletim manual de 25 min; CI/PRs espalhados no GitHub.
2. **Personas:** TL consolida; PO sem visão; devs sem alerta.
3. **Solução:** pipeline local API → Python → LLM → TTS → SQLite → n8n → WhatsApp.
4. **Prova:** `PULSE-20260917-121306-7999` success/github, 82,5 s, áudio + SQLite.
5. **Números:** 100% stress; 21 testes; ~94% menos tempo; 8,5 h/mês do TL.
6. **Tensão ética:** métrica não é ranking de pessoa.
7. **Responsabilidade:** LLM local, minimização, supervisão humana.
8. **Próximo:** cache GitHub, LLM assíncrono, Sheets no n8n (M1–M8).

## 4. Vídeo

- **Arquivo:** `video/DevOps-Pulse-Etapa3.mp4` (gerado a partir de slides do PDF + TTS pt-BR).
- **Roteiro ao vivo (se preferir gravar você):** `video/ROTEIRO-VIDEO.md` (~6 min).
- **Dica de gravação:** abra as abas no pré-check (`APRESENTACAO-ROTEIRO.md`) e fale em cima das evidências — não precisa reexecutar o pipeline LLM se o tempo estiver apertado (use o run já medido).

# Canvas — DevOps Pulse AI

| Campo | Conteúdo |
|-------|----------|
| **Problema** | Informações de desenvolvimento (issues, PRs, commits, CI/CD) ficam espalhadas; a consolidação manual consome tempo e atrasa decisões. |
| **Público** | Tech leads, gerentes de engenharia, equipes de software. |
| **Objetivo** | Produzir um boletim operacional automatizado com indicadores, alertas e resumo executivo. |
| **Proposta de valor** | Menos esforço manual, rastreabilidade por `execution_id`, IA local (privacidade) e canais de entrega (e-mail/WhatsApp). |
| **Entradas** | GitHub API (commits, issues, PRs, workflow runs). |
| **Processamento** | Microsserviço Python: normalização → métricas → alertas → Ollama → Kokoro → persistência. |
| **Saídas** | JSON `/api/pulse`, resumo em texto, áudio, registros SQLite, notificações. |
| **Canais** | API HTTP, n8n, e-mail, WhatsApp, dashboard. |
| **Recursos** | Python 3.12, FastAPI, n8n, Ollama, Kokoro, SQLite, Docker (opcional). |
| **Tecnologias** | FastAPI, httpx, pydantic, tenacity, pytest, n8n, Ollama, Kokoro TTS. |
| **Indicadores** | Commits, PRs, issues, taxa de sucesso CI, latências por etapa, taxa de sucesso do pipeline. |
| **Riscos** | API indisponível, rate limit, Ollama lento, TTS fora, alucinação, vazaento de token. |
| **Mitigações** | Retry, demo mode rotulado, fallback texto, `.env` + `.gitignore`, prompt restritivo, supervisão humana. |
| **Entregáveis** | Microsserviço, workflows n8n, testes, stress test, dashboard, documentação, evidências, vídeo. |
| **Papéis (equipe 6)** | **TL (1 dos 5 devs):** dono do boletim, risco de CI/PR e revisão técnica. **Devs (4):** implementação, testes, integrações e consumo do status. **PO (1):** prioridade, requisitos, aceite e visão de valor/ROI. Detalhe em `docs/diagnostico.md` §4. |
| **Objetivos (SMART)** | O1–O10 em `PROJECT.md` (coletar, indicar, resumir, áudio, orquestrar, persistir, multicanal, robustez, performance, avaliação). |

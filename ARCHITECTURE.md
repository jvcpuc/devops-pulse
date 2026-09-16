# Arquitetura — DevOps Pulse AI

## Visão geral

```text
GitHub API (ou demo)
        │
        ▼
Microsserviço Python (FastAPI :8000)
  github_client → metrics → alerts
        │
        ├─► Ollama (LLM local) ──► summary
        ├─► Kokoro (TTS) ──► .wav
        └─► SQLite (executions)
        │
        ▼
     n8n (:5678)
        ├── E-mail
        └── WhatsApp
        │
        ▼
   Dashboard / data/results
```

## Responsabilidades

| Componente | Responsabilidade |
|------------|------------------|
| **Python** | Coleta, normalização, métricas, alertas, validação, logs, latências, endpoint HTTP, pipeline CLI |
| **n8n** | Schedule, orquestra canais, fallback de notificação, registro de execução do fluxo |
| **Ollama** | Somente interpretação dos indicadores (não recebe dados brutos desnecessários) |
| **Kokoro** | TTS do resumo |
| **SQLite** | Histórico de execuções |

## Contrato `/api/pulse`

Resposta alinhada à especificação (campos + `execution_id`, `timings`, `data_source`):

```json
{
  "generated_at": "...",
  "execution_id": "PULSE-20260915-200001-A1B2",
  "repository": "OWNER/REPO",
  "period": { "from": "...", "to": "..." },
  "metrics": { "commits": 0, "workflow_success_rate": 0.0 },
  "alerts": [],
  "collection_latency_ms": 0,
  "status": "success",
  "data_source": "github"
}
```

## Tratamento de falhas

| Falha | Comportamento |
|-------|----------------|
| GitHub API | Retry (tenacity) → erro 502 no `/api/pulse`; pipeline registra `COLLECTION_ERROR` |
| Ollama | Fallback de texto rotulado + `LLM_ERROR` |
| Kokoro | Continua sem áudio + `TTS_ERROR` |
| SQLite | `PERSISTENCE_ERROR`, pipeline vira `partial` |
| WhatsApp (n8n) | `onError: continue` — e-mail não é perdido |

## Segurança

- Sem secrets no repositório;
- CORS aberto apenas para demo local do dashboard;
- Timeouts em toda integração externa.

## Decisões de design

1. **SQLite como default** — o enunciado aceita “banco simples”; Sheets fica no n8n.
2. **Modo demo explícito** — valida o pipeline sem token e sem fabricar métricas de produção.
3. **Ollama recebe só métricas + alertas** — minimização de dados e redução de alucinação.
4. **execution_id gerado no Python** — rastreia a execução mesmo se o n8n for reiniciado.

# DevOps Pulse AI

> Boletim inteligente de operações de desenvolvimento: coleta indicadores de um repositório no GitHub, gera alertas, produz um resumo com LLM local (Ollama), converte em áudio (Kokoro TTS), persiste o histórico e notifica por WhatsApp via n8n.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![n8n](https://img.shields.io/badge/n8n-orquestração-EA4B71?logo=n8n&logoColor=white)](https://n8n.io/)
[![Ollama](https://img.shields.io/badge/Ollama-LLM%20local-000000)](https://ollama.com/)
[![License: academic](https://img.shields.io/badge/uso-acadêmico-blueviolet)](#-ética-e-lgpd)

---

## O problema

Commits, pull requests, issues e execuções de CI/CD ficam **espalhados** na interface do GitHub. Consolidar isso à mão todo dia demora, atrasa a detecção de risco e não vira boletim acionável para o time.

## A solução

Uma **linha de produção de dados** com IA **local**:

```text
GitHub API  →  Python (FastAPI)  →  métricas + alertas
                      │
                      ├─► Ollama   → resumo executivo (texto)
                      ├─► Kokoro   → boletim em áudio (.wav)
                      └─► SQLite   → histórico com execution_id
                      │
                      ▼
                   n8n  →  WhatsApp (grupo) / e-mail / Telegram
                      │
                      ▼
                 Dashboard HTML
```

**Princípio de design:** o LLM **não é fonte primária de dados**. Ele apenas interpreta indicadores já calculados pelo sistema — isso reduz alucinação e está alinhado a LGPD / IA responsável.

---

## Arquitetura

| Componente | Papel |
|------------|--------|
| **Python / FastAPI** (`app/`) | Coleta, normalização, métricas, alertas, retries, logs, pipeline HTTP/CLI |
| **Ollama** | Resumo em linguagem natural a partir de métricas + alertas |
| **Kokoro TTS** | Síntese do resumo em `.wav` |
| **SQLite** | Histórico de execuções (`execution_id`) |
| **n8n** | Schedule, orquestração multicanal, fallback de notificação |
| **Evolution API** | WhatsApp self-hosted (Baileys) para envio do boletim |
| **Dashboard** | Visualização estática que consome a API |

Detalhes: [`ARCHITECTURE.md`](ARCHITECTURE.md) · Requisitos: [`docs/requisitos.md`](docs/requisitos.md)

---

## Funcionalidades

- **Coleta real** da GitHub API (commits, PRs, issues, workflow runs) com timeout e retry  
- **Indicadores** de 24 h (configurável até 168 h): volume, stale PRs, taxa de sucesso de CI  
- **Alertas** com severidade e thresholds configuráveis em `.env`  
- **Resumo com LLM local** (Ollama) com fallback rotulado se o modelo falhar  
- **Áudio** via Kokoro (voz `pf_dora`) salvo em `data/results/audio/`  
- **Persistência** SQLite + endpoint de histórico  
- **n8n**: workflows Etapa 1 (pipeline) e Etapa 2 (multicanal)  
- **WhatsApp** via Evolution API (grupo de operações)  
- **Modo demo explícito** (`DEMO_MODE=true`) para validar sem token — **nunca** apresentar demo como produção  
- **Logs estruturados** JSON em `logs/app.log`  
- **Stress test** + relatório de performance com números medidos  

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| API | Python 3.12 · FastAPI · Pydantic · httpx · tenacity |
| LLM | Ollama (`llama3.2:1b` neste ambiente) |
| TTS | Kokoro FastAPI (Docker) |
| Banco | SQLite |
| Automação | n8n (Docker) |
| WhatsApp | Evolution API 2.x + Postgres |
| Infra local | Docker Compose |

---

## Estrutura do projeto

```text
devops-pulse/
├── app/                    # microsserviço FastAPI
│   ├── main.py             # endpoints HTTP
│   ├── pipeline.py         # coleta → métricas → LLM → TTS → persist
│   ├── github_client.py    # API GitHub + retry
│   ├── metrics.py          # indicadores
│   ├── alerts.py           # thresholds
│   ├── ollama_client.py    # resumo
│   ├── tts_client.py       # Kokoro
│   ├── persistence.py      # SQLite
│   └── ...
├── tests/                  # 21 testes (pytest)
├── n8n/                    # workflows importáveis
├── dashboard/              # HTML do boletim visual
├── scripts/                # stress test, relatório, start_services
├── docs/                   # requisitos, diagnóstico, testes
├── data/results/           # SQLite, áudios, JSON (gitignored)
├── ARCHITECTURE.md
├── ETHICS-LGPD.md
├── PERFORMANCE.md          # números medidos + premissas
└── PROJECT.md              # objetivos SMART
```

---

## Como rodar

### Pré-requisitos

- Python 3.12+
- Docker (n8n, Kokoro, Evolution API — opcionais conforme o cenário)
- Ollama instalado (opcional; sem ele o resumo cai em fallback)

### Setup

```powershell
cd devops-pulse
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# copie pulse.env.example → pulse.env (ou .env) e preencha
#   DEMO_MODE=false
#   GITHUB_OWNER=...
#   GITHUB_REPOSITORY=...
#   GITHUB_TOKEN=ghp_...
#   OLLAMA_MODEL=llama3.2:1b

# sobe dependências Docker locais (Ollama/Kokoro/n8n/Evolution)
.\scripts\start_services.ps1

# API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Status dos componentes |
| GET | `/api/pulse?hours=24` | Coleta + métricas + alertas |
| POST | `/api/pipeline/run` | Pipeline completo (`with_llm`, `with_tts`, `persist`) |
| GET | `/api/executions` | Histórico SQLite |

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/pulse?hours=24
curl -X POST "http://127.0.0.1:8000/api/pipeline/run?hours=24&with_llm=true&with_tts=true&persist=true"
```

### CLI

```powershell
python -m app              # pipeline local
python -m app --llm --tts  # com IA e áudio
python -m app --live       # ignora DEMO_MODE
```

### Testes

```powershell
pytest -q
# 21 passed
```

### Stress test

```powershell
python scripts/stress_test.py --requests 10,25,50
python scripts/generate_report.py
```

### Dashboard

Abra `dashboard/index.html` no navegador. Ele carrega `http://127.0.0.1:8000/api/pulse` e sobrepõe as latências do último pipeline completo.

### n8n

1. Abra `http://localhost:5678`
2. Importe `n8n/etapa1.json` e `n8n/etapa2_evolution_telegram.json`
3. Configure variáveis (`WHATSAPP_TO` ou grupo, apikey Evolution, tokens)
4. Execute manualmente para demo — o schedule é diário

---

## Demo mode vs produção

| `DEMO_MODE` | Comportamento |
|-------------|---------------|
| `true` | Dados **fictícios** rotulados; `data_source=demo`; status `partial` |
| `false` | GitHub API real; `data_source=github` |

**Não apresente dados demo como evidência de produção.**

---

## Performance medida (resumo)

Números deste ambiente — detalhes em [`PERFORMANCE.md`](PERFORMANCE.md).

| Cenário | Tempo |
|---------|------:|
| `/api/pulse` (só coleta) | ~6–8 s |
| Pipeline completo (coleta + Ollama + Kokoro + SQLite) | ~2–3 min |
| Stress 10/25/50 req · concorrência 5 | 100% sucesso · p95 ~6,6–7,3 s |
| Consolidar boletim **na mão** (premissa) | 25 min |

Gargalos: **Ollama** e **Kokoro** no pipeline cheio; **GitHub API** no pulse isolado.

---

## Ética e LGPD

Documento completo: [`ETHICS-LGPD.md`](ETHICS-LGPD.md)

- LLM interpreta indicadores calculados — não coleta PII e não é fonte primária  
- Tokens apenas em arquivo de ambiente gitignored  
- Minimização: Ollama recebe métricas + alertas, não o dump bruto da API  
- Supervisão humana no destino das notificações  

---

## Contingências

| Falha | Comportamento |
|-------|----------------|
| GitHub API | Retry (tenacity) → erro 502 no `/api/pulse` |
| Ollama | Texto fallback rotulado + `LLM_ERROR` |
| Kokoro | Pipeline segue sem áudio + `TTS_ERROR` |
| SQLite | `PERSISTENCE_ERROR`, status `partial` |
| Canal WhatsApp | `onError: continue` no n8n — outros canais não são perdidos |

---

## Objetivos SMART

Resumo em [`PROJECT.md`](PROJECT.md). Critério de sucesso de cada objetivo O1–O10 com evidência no código/testes/docs.

---

## Créditos

Projeto acadêmico **AI Factory** — disciplina de automação com IA e integrações.  
Monitorado neste ambiente: repositório público [`n8n-io/n8n`](https://github.com/n8n-io/n8n) em modo demonstração técnica.

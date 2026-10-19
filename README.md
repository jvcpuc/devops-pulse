# DevOps Pulse AI

> Boletim inteligente de operações de desenvolvimento: coleta indicadores de um repositório no GitHub, gera alertas, produz um resumo com LLM local (Ollama), converte em áudio (Kokoro TTS), persiste o histórico e notifica por WhatsApp via n8n. Expõe suas consultas como **ferramentas MCP** (Model Context Protocol) para clientes de IA compatíveis.

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
                      ├─► SQLite   → histórico com execution_id
                      │
                      ├─► Servidor MCP (/mcp) → ferramentas para clientes de IA
                      │
                      ▼
                   n8n  →  WhatsApp (grupo) / e-mail / Telegram
                      │
                      ▼
                 Dashboard HTML  (botões "Demonstração MCP" = cliente JSON-RPC real)
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
| **Servidor MCP** | Ferramentas padronizadas (Streamable HTTP em `/mcp` + stdio) para clientes de IA |
| **Dashboard** | Visualização estática que consome a API — e atua como cliente MCP na demonstração |

Detalhes: [`ARCHITECTURE.md`](ARCHITECTURE.md) · Requisitos: [`docs/requisitos.md`](docs/requisitos.md)

---

## Funcionalidades

- **Coleta real** da GitHub API (commits, PRs, issues, workflow runs) com timeout e retry  
- **Indicadores** de 24 h (configurável até 168 h): volume, stale PRs, taxa de sucesso de CI  
- **Alertas** com severidade e thresholds configuráveis em `.env`  
- **Servidor MCP**: mesmas consultas disponíveis como ferramentas para clientes de IA  
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
| MCP | `mcp` (SDK oficial Python) — Streamable HTTP + stdio |
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
│   ├── main.py             # endpoints HTTP + servidor MCP montado em /mcp
│   ├── mcp_server.py       # servidor MCP (7 ferramentas: 5 somente-leitura + estresse/boletim)
│   ├── pipeline.py         # coleta → métricas → LLM → TTS → persist
│   ├── github_client.py    # API GitHub + retry (aceita repositório por chamada)
│   ├── metrics.py          # indicadores
│   ├── alerts.py           # thresholds
│   ├── ollama_client.py    # resumo
│   ├── tts_client.py       # Kokoro
│   ├── persistence.py      # SQLite
│   └── ...
├── tests/                  # 42 testes (pytest) — inclui suíte MCP
├── n8n/                    # workflows importáveis
├── dashboard/              # HTML do boletim visual + seção "Demonstração MCP"
├── scripts/                # stress test, relatório, start_services, start_demo
├── docs/                   # requisitos, diagnóstico, testes, guia e relatório MCP
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
| GET | `/api/whatsapp/status` | Estado da Evolution API/WhatsApp (usado pelo dashboard) |
| GET | `/api/whatsapp/qr` | QR de pareamento + pairing code (cria a instância se preciso) |
| POST | `/mcp` | **Servidor MCP** (Streamable HTTP, JSON-RPC) |

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
# 42 passed (21 originais + 18 de MCP + 3 de WhatsApp)
```

### Stress test

```powershell
python scripts/stress_test.py --requests 10,25,50
python scripts/generate_report.py
```

### Dashboard

Abra `dashboard/index.html` no navegador. Ele carrega `http://127.0.0.1:8000/api/pulse` e sobrepõe as latências do último pipeline completo.

### Demonstração em um comando

```powershell
.\scripts\start_demo.ps1            # sobe API + MCP e abre o dashboard
.\scripts\start_demo.ps1 -ForceDemo # força dados de demonstração
```

### MCP — Model Context Protocol

**O que é, em uma frase:** o MCP é um padrão que permite que assistentes de IA (Claude, ChatGPT etc.) *descubram e usem* ferramentas de um programa — neste caso, as consultas do DevOps Pulse — sem integração sob medida.

**Como funciona aqui:** o servidor MCP roda **no mesmo processo da API** e expõe as consultas já existentes (sem duplicar regra de negócio) em dois transportes:

| Transporte | Endpoint / comando | Uso |
|------------|--------------------|-----|
| Streamable HTTP | `http://127.0.0.1:8000/mcp` | Página do dashboard e clientes MCP remotos locais |
| stdio | `python -m app.mcp_server` | Clientes que iniciam o servidor como subproceso (ex.: Claude Desktop) |

**Ferramentas disponíveis** — 5 somente-leitura + 2 com efeitos laterais declarados:

| Ferramenta | Parâmetros | Retorna | Efeito |
|------------|-----------|---------|--------|
| `get_repository_metrics` | `owner`, `repo`, `hours` (1–168), `demo` | Métricas gerais + alertas do período | somente leitura |
| `get_commit_activity` | `owner`, `repo`, `hours`, `demo` | Total, série diária e amostra de commits | somente leitura |
| `get_pull_requests` | `owner`, `repo`, `state` (open/closed/all), `limit`, `demo` | Lista de PRs com estado e datas | somente leitura |
| `get_issues` | `owner`, `repo`, `state`, `limit`, `demo` | Issues reais (PRs excluídos) | somente leitura |
| `analyze_repository_health` | `owner`, `repo`, `hours`, `demo` | Observações explicáveis com critérios e limitações | somente leitura |
| `run_stress_test` | `requests` (ex. `5,10`, máx. 150), `concurrency` (1–20), `endpoint` (`/health`, `/api/pulse`), `timeout_s` | Latência (média/p50/p95), sucesso e throughput por lote | **gera carga** no endpoint local |
| `run_full_bulletin` | `hours`, `with_llm`, `with_tts`, `send_whatsapp`, `demo` | Pipeline completo: métricas, resumo LLM, boletim, áudio, tempos | **LLM + TTS + SQLite + envio no WhatsApp** (texto + áudio anexado) |

`demo`: `true` força dados fictícios rotulados; `false` força o GitHub real; omitido usa o `DEMO_MODE` do servidor. Todo resultado traz `data_source` — **nunca apresente `demo` como produção**. `run_full_bulletin` verifica a conexão do WhatsApp **antes** de rodar: se a instância não estiver pareada, executa o pipeline e informa (sem enviar), com instrução para escanear o QR no dashboard.

**Configurar um cliente MCP** (ex.: Claude Code):

```powershell
# Streamable HTTP (recomendado para a demonstração)
claude mcp add devops-pulse --transport http http://127.0.0.1:8000/mcp

# ou stdio (para clientes tipo Claude Desktop)
claude mcp add devops-pulse -- .\.venv\Scripts\python.exe -m app.mcp_server
```

Exemplo de `claude_desktop_config.json` (stdio):

```json
{
  "mcpServers": {
    "devops-pulse": {
      "command": "C:\\PUC\\2_Semestre\\AIFactory\\devops-pulse\\.venv\\Scripts\\python.exe",
      "args": ["-m", "app.mcp_server"],
      "env": { "DEMO_MODE": "true" }
    }
  }
}
```

**Botões da página:** a seção "Demonstração MCP" do dashboard atua como um **cliente MCP real** — os botões enviam JSON-RPC (o protocolo de verdade) para `/mcp`, com estados aguardando/processando/concluído/erro, repositório e período selecionáveis. Inclui **Teste de estresse** (com eco do relatório na página), **Executar demonstração completa (com WhatsApp)** — as 5 ferramentas + `run_full_bulletin` (texto + áudio no WhatsApp) —, copiar resumo e limpar. A página ainda verifica **em background** o estado da Evolution API: se o WhatsApp não estiver conectado, exibe o botão **Mostrar QR do WhatsApp** com o QR de pareamento — e, com o QR aberto, passa a checar **a cada 5 s**, refletindo o pareamento **sem F5** (o QR some sozinho e o selo vira "conectado"; há também **Verificar agora**/**Atualizar QR**). Detalhes e roteiro: [`docs/mcp-demo.md`](docs/mcp-demo.md) · Relatório técnico: [`docs/mcp-relatorio.md`](docs/mcp-relatorio.md)

**Segurança:** 5 ferramentas somente leitura e 2 com efeitos laterais explícitos na descrição; validação de `owner`/`repo` (sem caminhos, URLs ou comandos); estresse restrito a endpoints locais whitelisted (sem URL arbitrária) com teto de 150 requisições; sem execução de shell; token do GitHub nunca sai do servidor nem aparece em logs/erros; servidor aceita apenas hosts/origens locais (proteção anti DNS-rebinding).

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

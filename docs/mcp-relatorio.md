# Relatório técnico — implementação do MCP no DevOps Pulse AI

> Registro do que foi feito, testado e do que ficou pendente. Nenhum teste é
> afirmado aqui sem ter sido executado nesta implementação.

## 1. Objetivo (conforme especificação)

Disponibilizar as consultas existentes do projeto (GitHub → métricas) como
ferramentas **Model Context Protocol**, preservando a API, o dashboard e os
testes atuais, com demonstração por botões na página HTML e inicialização
simplificada.

## 2. Levantamento do projeto (antes de codificar)

| Item | Encontrado |
|------|-----------|
| Linguagem/runtime | Python 3.12.13, venv em `.venv` |
| Framework | FastAPI (`app/main.py`), uvicorn porta 8000 |
| Gerenciador de pacotes | `requirements.txt` (sem lock file no projeto) |
| Página HTML | `dashboard/index.html` — estática; busca `GET /api/pulse`, fallback JSON local e amostra embutida |
| Consultas ao GitHub | `app/github_client.py` → `fetch_raw()` normaliza commits, issues, PRs e workflow runs |
| Métricas reais | `app/metrics.py` (`compute_metrics`): commits, issues abertas/fechadas, PRs abertos/fechados, stale PRs, execuções de CI, taxa de sucesso |
| Alertas | `app/alerts.py` (`generate_alerts`) com thresholds do ambiente |
| Tokens | Variáveis de ambiente via pydantic-settings (`.env`) + `pulse.env` carregado pelos scripts; gitignored |
| Testes | `pytest`, 21 testes; padrão: fixtures HTTP com `TestClient` e mocks sem rede |
| Implementação prévia de MCP | **Nenhuma** (única menção era o campo interno `availableInMCP` de um export do n8n) |

## 3. Arquivos novos

| Arquivo | Papel |
|---------|-------|
| `app/mcp_server.py` | Servidor MCP (5 ferramentas), app Streamable HTTP e entrada stdio |
| `tests/test_mcp_server.py` | 13 testes: cliente em memória, ponta a ponta HTTP, stdio, fio JSON-RPC do navegador e erros controlados |
| `scripts/start_demo.ps1` | Inicialização em um comando (API + MCP + dashboard) |
| `docs/mcp-demo.md` | Guia rápido de demonstração |
| `docs/mcp-relatorio.md` | Este relatório |
| `evidence/mcp/*.json` | Saídas reais das ferramentas (cliente oficial, navegador e GitHub real) |
| `evidence/14-mcp-dashboard.png` | Página com a seção "Demonstração MCP" executada no navegador real |

## 4. Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `app/main.py` | Monta o servidor MCP em `/mcp`; lifespan executa o session manager; CORS expõe `Mcp-Session-Id` |
| `app/github_client.py` | `GitHubClient(settings, repo_full_name=...)` permite consultar qualquer repositório (padrão inalterado) |
| `dashboard/index.html` | Seção "Demonstração MCP": campos, 8 botões, estados, JSON seguro (`textContent`, anti-XSS) e cliente JSON-RPC |
| `requirements.txt` | `mcp>=2.3.0,<3` |
| `README.md` | Seção MCP (ferramentas, transportes, configuração de cliente, segurança) e contagem de testes |
| `video/ROTEIRO-VIDEO.md` | Bloco MCP no roteiro de apresentação |
| `pulse.env.example` | Comentário: MCP não exige variáveis novas |

## 5. Dependências adicionadas

- `mcp` **2.3.0** (SDK oficial Python; instala `mcp-types`, `httpx2`,
  `sse-starlette>=3`, `opentelemetry-api`, `truststore`, `pyjwt`,
  `cryptography`, entre outras — todas transitivas do SDK).
- O projeto não usa lock file; a versão foi fixada por faixa em
  `requirements.txt` (`mcp>=2.3.0,<3`), seguindo o padrão existente.

## 6. Decisões de projeto

### SDK

SDK **oficial** `mcp` v2 (classe `MCPServer`, ex-`FastMCP`), consultando a
documentação atual — a API v2 renomeou símbolos e trocou `httpx` por `httpx2`
internamente; nada de exemplos obsoletos copiados.

### Transporte

- **Streamable HTTP montado na FastAPI** (`POST http://127.0.0.1:8000/mcp`):
  o projeto já roda essa API na porta 8000 — manter um único processo evita
  novo serviço e simplifica a demonstração. Modo `json_response` +
  `stateless_http`: respostas JSON diretas (sem SSE) e sem estado de sessão,
  o que torna o cliente do navegador trivial e permite múltiplos clientes
  simultâneos.
- **stdio** (`python -m app.mcp_server`): para clientes desktop que iniciam o
  servidor como subproceso. No stdio os logs são redirecionados para
  **stderr** (stdout é do protocolo — verificado por teste).
- **Segurança de transporte**: proteção anti DNS-rebinding ativa restrita a
  hosts locais (`localhost`, `127.0.0.1`, `[::1]`) e origens locais de
  navegador (incl. `null` para páginas `file://`). Nada exposto à rede
  externa.

### Página HTML

A seção "Demonstração MCP" **não** finge que HTTP comum é MCP: o JavaScript da
página implementa um cliente MCP mínimo que executa o handshake real
(`initialize` → `notifications/initialized` → `tools/call`) em JSON-RPC contra
`/mcp` — o mesmo ponto de extremidade usado por clientes externos.

### Reaproveitamento (sem duplicar negócio)

Todas as ferramentas chamam as funções existentes: `GitHubClient.fetch_raw()`
(normalização), `compute_metrics()`, `generate_alerts()` e `build_demo_raw()`.
As ferramentas apenas filtram/projetam o que já é coletado.

### Demo rotulado

Parâmetro `demo` por chamada (`true`/`false`/omitido = `DEMO_MODE` do
servidor). Todo resultado traz `data_source` e, em demo, nota explícita de que
os números são fictícios.

## 7. Ferramentas MCP implementadas

| Ferramenta | Parâmetros | Reutiliza |
|------------|-----------|-----------|
| `get_repository_metrics` | `owner`, `repo`, `hours` (1–168), `demo` | `fetch_raw` + `compute_metrics` + `generate_alerts` |
| `get_commit_activity` | `owner`, `repo`, `hours`, `demo` | `fetch_raw` + `_parse_dt` |
| `get_pull_requests` | `owner`, `repo`, `state`, `limit` (1–100), `demo` | `fetch_raw` |
| `get_issues` | `owner`, `repo`, `state`, `limit`, `demo` | `fetch_raw` (PRs já excluídos) |
| `analyze_repository_health` | `owner`, `repo`, `hours`, `demo` | `compute_metrics` + `generate_alerts` + thresholds |

Todas somente leitura; nenhuma aceita caminho, comando ou URL.

## 8. Testes executados e resultados

### Suíte completa (pytest)

```
pytest -q  →  34 passed  (21 originais + 13 novos, 0 falhas)
```

### Suíte MCP (`tests/test_mcp_server.py`) — 13 testes

| Teste | Valida |
|-------|--------|
| `test_lists_all_tools` | Cliente oficial descobre as 5 ferramentas com descrição |
| `test_get_repository_metrics_demo` | Métricas + alertas + período + nota de demo |
| `test_get_commit_activity_demo` | Total, série diária e amostra de commits |
| `test_get_pull_requests_state_filter_demo` | Filtro `open`/`all` e campos dos itens |
| `test_get_issues_excludes_pull_requests` | Issues reais (PRs excluídos) |
| `test_analyze_repository_health_demo` | Observações, critérios e limitações documentadas |
| `test_invalid_owner_is_controlled_error` | `owner` inválido → erro compreensível |
| `test_invalid_hours_is_controlled_error` | Fora de 1–168 → erro de validação |
| `test_unknown_tool_is_controlled_error` | Ferramenta inexistente → erro controlado |
| `test_github_api_failure_is_controlled_error` | 404 da API → mensagem legível, sem crash |
| `test_streamable_http_end_to_end` | **Cliente oficial real** conecta via HTTP, lista e executa duas ferramentas |
| `test_stdio_transport_end_to_end` | **Subproceso real** `python -m app.mcp_server`: lista, executa e não corrompe o protocolo com logs |
| `test_browser_jsonrpc_wire` | Preflight CORS + `initialize` + notificação + `tools/call` + erro, exatamente como o navegador envia |

### Validação ao vivo (API em execução real)

- Cliente oficial (SDK) contra `http://127.0.0.1:8000/mcp`:
  listou as 5 ferramentas; executou `get_repository_metrics` e
  `get_commit_activity` (evidências em `evidence/mcp/client-*.json`).
- **GitHub real**: `get_repository_metrics` de `n8n-io/n8n` (últimas 24 h,
  `demo=false`) retornou `data_source: github` com 2 commits, 18 PRs
  abertos, taxa de CI 62% e 3 alertas
  (`evidence/mcp/client-get-repository-metrics-GITHUB-REAL.json`).
- Navegador real (Chromium/Playwright) na página `file://`:
  preflight CORS 200, e o botão "Executar demonstração completa" executou as
  5 ferramentas em sequência com status "concluído"
  (`evidence/14-mcp-dashboard.png`).
- Erro controlado ao vivo: `owner=".."` → `isError: true` com mensagem
  explicando o formato aceito.

## 9. Limitações e itens não concluídos

- **Paginação**: as ferramentas leem a primeira página da API do GitHub
  (até 100 itens por tipo). A limitação é informada em `notes` de cada
  resposta.
- **Índice de saúde**: `analyze_repository_health` **não** gera pontuação
  composta (decisão da especificação: evitar índice arbitrário); apresenta
  observações individuais com critérios e thresholds configurados.
- **structuredContent**: as ferramentas retornam `dict`, que o SDK entrega
  como JSON em conteúdo textual (clientes e IA leem normalmente). Schema de
  saída tipado (Pydantic) seria um passo futuro.
- **Cliente do navegador**: usa handshake completo a cada chamada (3
  mensagens) por simplicidade; uma versão com cache de sessão reduziria
  idas e vindas.
- **Sessão**: servidor em modo stateless — adequado a ferramentas de leitura;
  recursos que exijam mensagens servidor→cliente exigiriam modo com sessão.
- **Capturas de tela** foram feitas via Chromium headless; em máquina sem
  Playwright, use as evidências já salvas.

# Guia rápido de demonstração — MCP no DevOps Pulse AI

> Objetivo: reproduzir a demonstração do MCP em ~10 minutos, sem digitar
> comandos repetidos. Complementa o roteiro de apresentação
> (`video/ROTEIRO-VIDEO.md`, bloco MCP).

## 1. Preparação prévia (antes da aula)

- [ ] `pip install -r requirements.txt` já executado (instala o SDK `mcp`).
- [ ] `pulse.env` (ou `.env`) preenchido; para demonstração determinística use
      `DEMO_MODE=true` ou inicie com `.\scripts\start_demo.ps1 -ForceDemo`.
- [ ] Executar `pytest -q` → esperado: **34 passed**.
- [ ] Se for usar um cliente de IA (ex.: Claude Code), configurar antes:
      `claude mcp add devops-pulse --transport http http://127.0.0.1:8000/mcp`
- [ ] Fechar janelas/token que não devem aparecer em capturas.
- [ ] Ter em mãos as capturas de contingência em `evidence/mcp/` e
      `evidence/14-mcp-dashboard.png`.

## 2. Inicialização (um comando)

```powershell
.\scripts\start_demo.ps1
```

O script carrega o ambiente, sobe a API FastAPI (que também hospeda o
servidor MCP em `http://127.0.0.1:8000/mcp`) e abre o dashboard no
navegador. Verificação rápida:

```powershell
curl http://127.0.0.1:8000/health
```

## 3. Passos exatos da apresentação

### A) Página HTML (2 min)

1. Abra `dashboard/index.html` (o script já abre).
2. Mostre que as métricas de antes continuam lá (cards, alertas, timings).
3. Role até **"Demonstração MCP"**.
4. Mantenha `n8n-io / n8n`, período 24 h e "padrão do servidor".
5. Clique em **Consultar métricas** → mostre o estado "processando" →
   "concluído" → o JSON com badge `github real` ou `dados demo`.
6. Clique em **Consultar commits** (ou pull requests) — segunda ferramenta.
7. Demonstre um erro compreensível: troque o owner para `..` e clique em
   Consultar métricas → aparece a mensagem de erro na área de resultados.
8. **Executar demonstração completa** → as 5 ferramentas em sequência, sem
   chamadas duplicadas.
9. **Copiar resumo** → cola em um bloco de notas como evidência.

> Explique: os botões falam JSON-RPC com `/mcp` — a página é um cliente MCP.
> A validação do protocolo, porém, é o próximo passo, com um cliente real.

### B) Cliente MCP real (2–3 min)

1. Abra o terminal do cliente configurado (ex.: Claude Code na pasta do
   projeto).
2. Mostre a lista de ferramentas descobertas (o cliente faz `tools/list`).
3. Peça: **"Consulte as métricas do repositório n8n-io/n8n"**
   (`get_repository_metrics`).
4. Peça uma segunda ferramenta: **"Como foi a atividade de commits nas
   últimas 24 horas?"** (`get_commit_activity`).
5. Se houver IA configurada, pergunte: **"Com base nos dados retornados,
   quais pontos merecem atenção?"** (o modelo lê os alertas retornados).

Alternativa sem IA: mostrar a saída de um cliente MCP "sem modelo", apenas
listando e executando ferramentas.

## 4. Perguntas de demonstração (e o que esperar)

| Pergunta | Ferramenta | Resultado esperado |
|----------|-----------|--------------------|
| "Consulte as métricas deste repositório" | `get_repository_metrics` | JSON com `metrics` (commits, PRs, CI…) e `alerts` |
| "Como foi a atividade de commits?" | `get_commit_activity` | `total_commits` + `daily_series` |
| "Quais pull requests estão pendentes?" | `get_pull_requests` com `state=open` | Itens com `state: open` |
| "Que pontos merecem atenção?" | `analyze_repository_health` | `observations` com critérios e limites |
| "E para um repositório inexistente?" | qualquer | Erro controlado (não crash) |

Não pergunte sobre dados que as ferramentas não fornecem (ex.: qualidade de
código, segurança, dados de pessoas).

## 5. Plano alternativo (se a API/GitHub falhar)

1. **GitHub fora do ar ou rate limit:** use `demo=true` na ferramenta (ou
   selecione "forçar dados demo" na página) e diga explicitamente que são
   dados fictícios rotulados.
2. **API local não sobe:** mostre `evidence/14-mcp-dashboard.png` (página com
   botões em uso) e `evidence/mcp/*.json` (saídas reais já capturadas) —
   deixe claro que são evidências de uma execução anterior.
3. **Cliente de IA indisponível:** rode a validação sem modelo:
   `pytest tests\test_mcp_server.py -q` e mostre os 13 testes passando,
   incluindo a conexão real do cliente oficial via Streamable HTTP e stdio.

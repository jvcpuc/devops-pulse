# Guia rápido de demonstração — MCP no DevOps Pulse AI

> Objetivo: reproduzir a demonstração do MCP em ~10 minutos, sem digitar
> comandos repetidos. Complementa o roteiro de apresentação
> (`video/ROTEIRO-VIDEO.md`, bloco MCP).

## 1. Preparação prévia (antes da aula)

- [ ] `pip install -r requirements.txt` já executado (instala o SDK `mcp`).
- [ ] `pulse.env` (ou `.env`) preenchido; para demonstração determinística use
      `DEMO_MODE=true` ou inicie com `.\scripts\start_demo.ps1 -ForceDemo`.
- [ ] Executar `pytest -q` → esperado: **42 passed**.
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
8. **Teste de estresse** → roda a ferramenta `run_stress_test` (lotes de
   requisições contra `/health`) e ecoa o relatório com latência p95,
   sucesso e throughput por lote.
9. **Executar demonstração completa (com WhatsApp)** → as 5 ferramentas em
   sequência, sem chamadas duplicadas, e em seguida `run_full_bulletin`:
   pipeline completo (LLM + áudio TTS + SQLite) com envio no WhatsApp
   (texto + áudio anexado). Se o WhatsApp não estiver pareado, informa
   claramente (sem enviar) e orienta a escanear o QR.
10. **Copiar resumo** → cola em um bloco de notas como evidência.

> **WhatsApp em background:** a página verifica sozinha o estado da Evolution
> API (a cada 30 s; a cada **5 s** enquanto o QR está aberto, para refletir o
> pareamento **sem F5**). Se o WhatsApp não estiver conectado, aparece o botão
> **Mostrar QR do WhatsApp** — clique para exibir o QR de pareamento
> (WhatsApp → Aparelhos conectados → Conectar aparelho; **o QR expira em
> ~20 s**, use **Atualizar QR** se precisar de novo). Assim que você conecta,
> o QR some sozinho e o selo vira "WhatsApp conectado" ✅. Há também o botão
> **Verificar agora** para checar o estado na hora; se a sessão cair, a
> página avisa ("WhatsApp desconectado") em vez de mentir.

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
| "Teste a resistência do serviço" | `run_stress_test` | `batches` com p95, sucesso e throughput |
| "Execute o boletim completo e avise no WhatsApp" | `run_full_bulletin` | Pipeline completo + envio (texto + áudio) |
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
   `pytest tests\test_mcp_server.py -q` e mostre os 18 testes passando,
   incluindo a conexão real do cliente oficial via Streamable HTTP e stdio.

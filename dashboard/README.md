# Dashboard

Abra `index.html` no navegador (duplo clique ou `start dashboard\index.html`).

## Como usar com dados reais

1. Execute o pipeline:

   ```powershell
   python -m app.pipeline
   ```

2. Copie o JSON retornado para um arquivo, ou:

   ```powershell
   # exemplo: salvar a resposta da API
   curl http://127.0.0.1:8000/api/pulse -o data\results\last_pulse.json
   ```

3. No dashboard, use **Escolher arquivo** e selecione o JSON.

## Páginas da história

O HTML único cobre as 4 páginas pedidas no documento:

1. Cards executivos (commits, PRs, issues, CI, alertas)
2. Performance (barras de latência por etapa)
3. Evolução (acumule execuções na tabela ao carregar vários JSONs)
4. Automação (bloco antes × depois — preencher com tempos medidos)

Para um dashboard multi-execução em produção, conecte ao endpoint `/api/executions` ou ao SQLite.

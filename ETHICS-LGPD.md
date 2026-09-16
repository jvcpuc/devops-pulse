# LGPD e IA responsável — DevOps Pulse AI

## 1. Minimização

O sistema coleta apenas metadados operacionais de repositório:

- contagens e timestamps de commits;
- número/título/state de issues e PRs;
- status/conclusão de workflow runs.

**Não coletamos** corpos de commits, diffs, conteúdo de issues, e-mails de terceiros além do necessário para notificação configurada pelo operador.

## 2. Finalidade

Finalidade única: gerar **boletim operacional** para apoio à gestão de desenvolvimento.

## 3. Transparência

| Item | Prática |
|------|---------|
| Fonte | GitHub API (ou demo rotulado) |
| Processamento | Microsserviço local Python |
| Interpretação | Ollama (LLM local) — opcional |
| Áudio | Kokoro (local) — opcional |
| Armazenamento | SQLite local (`data/results/`) |
| Destinatários | Operador via API; e-mail/WhatsApp configurados explicitamente |

## 4. Segurança

- Credenciais **apenas** em `.env` (não versionado);
- `.gitignore` cobre `.env`, áudios e resultados;
- Tokens não entram em logs estruturados (não são logados);
- Integrações usam timeout e tratamento de erro.

## 5. IA responsável

| Princípio | Implementação |
|-----------|---------------|
| LLM não é fonte primária | Dados vêm da API + `metrics.py` |
| Anti-alucinação | Prompt proíbe inventar incidentes/causas/pessoas |
| Separação fato × interpretação | JSON de métricas separado do `summary` |
| Fallback honesto | Se Ollama falha, texto técnico rotulado `NÃO foi produzido por LLM` |
| Rastreabilidade | `execution_id` em todos os estágios |
| Supervisão humana | Resumo é apoio; decisões críticas exigem revisão |

## 6. Dados pessoais

Mesmo com API pública, usernames/avatars **não são persistidos** no SQLite por padrão — apenas contagens e números de issues/PRs.

Se no futuro for necessário identificar autores:

1. justificar a finalidade;
2. preferir agregação/anonimização;
3. documentar retenção e descarte.

## 7. Retenção

- SQLite local: controlada pelo operador (pode apagar `data/results/pulse.db`);
- Áudios: podem ser removidos após a apresentação;
- Logs: `logs/app.log` — sem segredos.

## 8. Limitações declaradas

- `DEMO_MODE=true` usa dados fictícios;
- LLM local pode alucinar se o prompt for descuidado — o código fixa um prompt restritivo;
- WhatsApp/e-mail dependem de credenciais do operador e de opt-in do destinatário.

# Plano de testes

## Unitários (`pytest`)

| Área | Arquivo | Cobre |
|------|---------|-------|
| Métricas | `tests/test_metrics.py` | taxa de sucesso, janela temporal, dados ausentes |
| Alertas | `tests/test_alerts.py` | CI_FAILURE, STALE_PR, thresholds, unusual activity |
| GitHub client | `tests/test_github_client.py` | headers/token, repo ausente, erros |
| API | `tests/test_api.py` | `/health`, `/api/pulse`, pipeline, executions |

Executar:

```powershell
pytest -q
```

## Integração (manual / ambiente)

```text
API → Python → Ollama → Kokoro → persistência
```

1. Iniciar Ollama: `ollama serve` + `ollama pull <modelo>`
2. Configurar `.env` (`DEMO_MODE=false`, repo, token)
3. `POST /api/pipeline/run?with_llm=true&with_tts=true`
4. Conferir `data/results/pulse.db` e `data/results/audio/`

## Fluxo n8n

1. Importar `n8n/etapa1.json` e executar manualmente
2. Importar `n8n/etapa2.json` (requer SMTP/WhatsApp configurados)
3. Conferir `execution_id` no log e na resposta

## Stress test

```powershell
# com API no ar
python scripts/stress_test.py --requests 10,25,50,100
```

Métricas coletadas: success, errors, avg/min/max, p50, p95, RPS.

## Regras

- Não fabricar resultados.
- Todo número no trabalho final deve ter origem em `data/results/`.
- Dados `DEMO_MODE` são evidência de **funcionamento do pipeline**, não de métricas de repositório real.

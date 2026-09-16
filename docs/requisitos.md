# Matriz de requisitos

| ID | Requisito | Tipo | Prioridade | Evidência | Status no código |
|----|-----------|------|------------|-----------|------------------|
| RF01 | Consumir API pública (GitHub) | Funcional | Alta | Log + JSON | `app/github_client.py` |
| RF02 | Calcular indicadores | Funcional | Alta | JSON | `app/metrics.py` |
| RF03 | Usar Ollama | Funcional | Alta | Log + summary | `app/ollama_client.py` |
| RF04 | Usar Kokoro | Funcional | Alta | Arquivo áudio | `app/tts_client.py` |
| RF05 | Persistir resultado | Funcional | Alta | SQLite/DB | `app/persistence.py` |
| RF06 | Integrar n8n | Funcional | Alta | Workflow | `n8n/etapa1.json`, `etapa2.json` |
| RF07 | Enviar e-mail | Funcional | Alta | Mensagem | n8n Etapa 2 |
| RF08 | Enviar WhatsApp | Funcional | Alta | Mensagem | n8n Etapa 2 |
| RF09 | Tratamento de erros + retry | Não funcional | Alta | Logs | tenacity + fallbacks |
| RF10 | Stress test | Não funcional | Alta | Relatório JSON | `scripts/stress_test.py` |
| RF11 | Dashboard | Entregável | Alta | HTML | `dashboard/index.html` |
| RF12 | LGPD / IA responsável | Compliance | Alta | Documento | `ETHICS-LGPD.md` |
| RF13 | Variáveis de ambiente | Não funcional | Alta | `.env.example` | `app/config.py` |
| RF14 | Logs estruturados | Não funcional | Alta | `logs/app.log` | `app/logging_config.py` |
| RF15 | execution_id rastreável | Funcional | Alta | JSON/logs | `app/pipeline.py` |
| RF16 | Alertas configuráveis | Funcional | Média | JSON alerts | `app/alerts.py` + thresholds |

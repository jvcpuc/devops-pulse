# Apresentação — DevOps Pulse AI

## Storytelling (8 blocos)

1. **Problema** — informações importantes espalhadas em issues, PRs, commits e CI.
2. **Impacto** — consolidação manual, atraso na detecção de riscos.
3. **Solução** — linha de produção de dados com IA local.
4. **Como funciona** — `API → Python → n8n → Ollama → Kokoro → canais`.
5. **Resultado** — números reais de latência, taxa de sucesso, execuções.
6. **Limitações** — dependências, falhas, limites do LLM.
7. **Ética** — LGPD, minimização, supervisão humana.
8. **Próximos passos** — mais repositórios, baseline de anomalias, Sheets nativo.

## Roteiro do vídeo (~6 min)

| Tempo | Bloco |
|------:|-------|
| 0:00–0:40 | Problema (processo manual) |
| 0:40–1:20 | Objetivo do projeto |
| 1:20–2:20 | Arquitetura |
| 2:20–3:30 | Demonstração ao vivo |
| 3:30–4:30 | Dashboard e métricas |
| 4:30–5:20 | Stress test e gargalos |
| 5:20–6:00 | LGPD, IA responsável, conclusão |

## Script da demo ao vivo

```powershell
# 1. Health
curl http://127.0.0.1:8000/health

# 2. Pulse (indicadores)
curl http://127.0.0.1:8000/api/pulse

# 3. Pipeline completo
curl -X POST "http://127.0.0.1:8000/api/pipeline/run?hours=24"

# 4. n8n — executar workflow Etapa 1

# 5. Dashboard — abrir dashboard/index.html

# 6. Stress test
python scripts/stress_test.py --requests 10,25
```

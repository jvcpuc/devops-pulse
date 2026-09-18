# Performance — DevOps Pulse AI

> Números **medidos** neste ambiente (2026-09-16/17). Premissas manuais marcadas como tal.
> Etapa 3: análise de performance, ROI e **proposta de melhorias**.

## Pipeline completo medido (LLM + TTS + SQLite)

| Execução | Status / fonte | Coleta | LLM | TTS | Total |
|----------|----------------|-------:|----:|----:|------:|
| `PULSE-20260916-183616-6C1A` | success / github | 27,7 s | 57,7 s | 84,3 s | **170,0 s** |
| `PULSE-20260917-121306-7999` | success / github | 5,5 s | 58,5 s | 18,6 s | **82,5 s** |
| `/api/pulse` isolado (sem LLM/TTS) | — | ~6–8 s | — | — | **~6–8 s** |

Variação: rede (GitHub) e tempo de síntese do Kokoro (cache/warmup).

## Taxa de sucesso

| Indicador | Valor medido | Origem |
|-----------|-------------:|--------|
| Stress `/api/pulse` 10/25/50 req | **100%** success | `stress_test_20260916-143900.json` |
| p50 / p95 (stress) | 6,3 s / 6,6–7,3 s | idem |
| RPS sob concorrência 5 | ~0,75–0,81 | idem |
| Pipeline completo (LLM+TTS) | success com fallbacks rotulados | logs + SQLite |
| Testes automatizados | **21/21** pytest | `pytest -q` |
| Execuções persistidas | 17 linhas em `executions` | `pulse.db` |

Gargalo do stress: **chamada HTTP à GitHub API** a cada request (~6 s).

## ROI / valor de negócio (tempo)

| Cenário | Tempo | Origem |
|---------|------:|--------|
| **Manual** | **25 min**/boletim | Premissa do contexto (GitHub UI + resumo + envio) |
| **Automatizado** | **~1,4 min** (82,5 s) | Pipeline medido `PULSE-20260917-121306-7999` |
| **Redução** | **~94%** | `(25 − 1,4) / 25` |
| Supervisão da automação | ~2 min/dia | Dashboard + alertas |

```text
horas_manual_mes    = (25 / 60) × 22 ≈ 9,2 h
horas_automacao_mes = (2 / 60) × 22  ≈ 0,7 h
horas_economizadas  ≈ 8,5 h/mês do TL
```

**Não converter em R$** sem valor/hora documentado da equipe.

### Impacto qualitativo (storytelling)

- **Detecção mais cedo:** alertas de CI/stale PR chegam no grupo, não “quem lembrar”.
- **Rastreabilidade:** `execution_id` liga JSON → SQLite → WhatsApp.
- **Menos ponto único de falha:** TL não é mais o único consolidador.
- **Privacidade:** LLM local — indicadores não saem da máquina.

## Gargalos confirmados

1. **Ollama** — estágio mais lento (~58 s)
2. **Kokoro** — segundo maior (~19–84 s)
3. **GitHub API** — domina `/api/pulse` (~6 s)
4. **SQLite** — dezenas de ms (irrelevante)

## Propostas de melhoria (Etapa 3)

| # | Melhoria | Base nos dados | Impacto esperado | Esforço |
|---|----------|----------------|------------------|---------|
| M1 | **Cache da coleta GitHub** (5–10 min) | Stress: 100% do tempo em HTTP GitHub | Reduz `/api/pulse` de ~6 s para <1 s em cache hit; p95 cai | Médio |
| M2 | **LLM assíncrono / paralelo** | LLM ~58 s serial após coleta | Pipeline “texto pronto” em ~8 s; áudio em background | Médio |
| M3 | **Modelo TTS em cache / Kokoro warm** | TTS variou 18–84 s | Total do pipeline mais estável (p95 menor) | Baixo |
| M4 | **Múltiplos repositórios + paginação** | Hoje 1 repo (`n8n-io/n8n`) | Escala para squad com 2–3 monorepos | Médio |
| M5 | **Google Sheets no n8n** (entrega extra) | SQLite local não é multiusuário | PO/LP acessam histórico sem SSH na máquina | Baixo |
| M6 | **Baseline de anomalias** (volume/CI) | Thresholds fixos hoje | Menos alerta falso; foco em desvio real | Alto |
| M7 | **Video/áudio opcional no boletim diário** | TTS 19–84 s | Daily “ouvir” só se TL marcar `with_tts` | Baixo |
| M8 | **Observabilidade** (métricas do pipeline no dashboard) | Já há timings por estágio | Alerta de regressão (ex.: LLM > 90 s) | Médio |

**Prioridade sugerida:** M1 → M2/M3 → M5 → M4 → M6/M8.

## Como regerar

```powershell
python scripts/stress_test.py --requests 10,25,50
python scripts/generate_report.py
```

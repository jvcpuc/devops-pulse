# Performance — DevOps Pulse AI

> Números **medidos** neste ambiente (2026-09-16). Premissas manuais marcadas como tal.

## Pipeline completo medido (LLM + TTS + SQLite)

Execução de referência: `PULSE-20260916-183616-6C1A` (`status=success`, `data_source=github`)

| Estágio | Latência medida |
|---------|----------------:|
| Coleta GitHub API | 27 697 ms |
| Ollama (`llama3.2:1b`) | 57 718 ms |
| Kokoro TTS | 84 343 ms |
| **Total pipeline** | **170 006 ms (~2,8 min)** |

Outro run no mesmo dia (`PULSE-20260916-142747-27D7`): total 109 578 ms (coleta 7,7 s · LLM 57 s · TTS 45 s).  
A variação vem de rede (GitHub) e do tempo de síntese do Kokoro.

> `/api/pulse` isolado (sem LLM/TTS) fica em ~6–8 s — é só a coleta.

## Stress test `/api/pulse` (2026-09-16)

Arquivo: `data/results/stress_test_20260916-143900.json`  
Concorrência: 5 · 100% de sucesso

| Requests | Success | Errors | p50 (ms) | p95 (ms) | RPS |
|---------:|--------:|-------:|---------:|---------:|----:|
| 10 | 10 | 0 | 6 385 | 6 730 | 0,76 |
| 25 | 25 | 0 | 6 301 | 7 265 | 0,75 |
| 50 | 50 | 0 | 6 011 | 6 611 | 0,81 |

Gargalo dominante: **chamada HTTP à GitHub API** a cada request.

## Antes × Depois (dashboard)

| Cenário | Tempo | Origem |
|---------|------:|--------|
| **Manual** | **25 min** | Premissa do contexto (abrir GitHub UI, filtrar 24 h, contar commits/PRs/issues/CI, redigir resumo, enviar e-mail/WhatsApp) |
| **Automatizado** | **~2,8 min** | Medido no pipeline (`PULSE-20260916-183616-6C1A`: coleta + Ollama + Kokoro + SQLite) |
| Redução | ~89% | `(25 − 2,8) / 25` |

### Premissas manuais (explícitas)

```text
Tempo médio manual por relatório = 25 minutos   → premissa (ajuste se tiver cronometrado)
Relatórios por mês               = 22 (dias úteis)
Tempo de supervisão da automação = 2 minutos     → abrir dashboard + checar alertas
```

Economia de tempo (sem conversão financeira):

```text
horas_manual_mes      = (25 / 60) × 22 ≈ 9,2 h
horas_automacao_mes   = (2 / 60) × 22  ≈ 0,7 h
horas_economizadas    ≈ 8,5 h/mês
```

Não apresentar custo em R$ sem valor/hora documentado da equipe.

## Gargalos confirmados

1. **Ollama** — estágio mais lento (~57 s no run de referência)
2. **Kokoro** — segundo maior (~45 s)
3. **GitHub API** — domina o `/api/pulse` isolado (~6 s)
4. **SQLite** — dezenas de ms (irrelevante)

## Como regerar

```powershell
python scripts/stress_test.py --requests 10,25,50
python scripts/generate_report.py
```

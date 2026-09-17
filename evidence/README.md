# Evidências — DevOps Pulse AI

Capturas geradas em **2026-09-17** com o ambiente real (`DEMO_MODE=false`, repo `n8n-io/n8n`).

Pipeline de referência: **`PULSE-20260917-121306-7999`**  
status `success` · `data_source=github` · total **82,5 s** · áudio + resumo LLM gravados.

## Inventário

| Arquivo | O que prova | Status |
|---------|-------------|--------|
| `01-api-health.png` / `02-python.png` | `/health` com GitHub, Ollama, Kokoro, n8n OK | OK |
| `01-api.png` / `01-api-text.png` | `/api/pulse` com métricas reais do GitHub | OK |
| `02b-pytest.png` | 21/21 testes verdes | OK |
| `03-n8n-etapa1.png` | Workflows DevOps Pulse no n8n (CLI + API) | OK |
| `03-n8n-etapa1-diagram.png` | Diagrama do fluxo Etapa 1 | OK |
| `03-n8n-login.png` | Tela de login do n8n (UI protegida) | OK |
| `04-ollama.png` | Modelo `llama3.2:1b` disponível | OK |
| `05-kokoro.png` | `.wav` gerado pelo Kokoro (`pf_dora`) | OK |
| `06-planilha.png` | SQLite `executions` com `execution_id` | OK |
| `07-n8n-etapa2.png` | Etapa 2 multicanal listada | OK |
| `07-evolution-manager.png` | Evolution API no ar | OK |
| `08-email.png` | Canal e-mail (reserva) — sem inbox real capturada | Parcial |
| `09-whatsapp.png` | Envio ao grupo via Evolution API | OK |
| `whatsapp.png` | Print da conversa (boletim completo no grupo) | OK |
| `10-dashboard.png` | Dashboard com cards, alertas, latências | OK |
| `11-stress-test.png` | Stress test JSON | OK |
| `12-logs.png` | `logs/app.log` estruturado | OK |
| `13-github*.png` | Repo / Actions / PRs públicos monitorados | OK |
| `whatsapp-qr.png` | Pareamento WhatsApp (histórico) | OK |

## Arquivos de dados (não são prints)

- `health.json`, `api-pulse.json`, `executions.json`, `pipeline-full.json`
- `whatsapp-send.json` (resposta da Evolution API)
- `pytest-output.txt`, `logs-tail.txt`
- `n8n-workflows-export.json` (export dos 5 workflows)

## Ainda faltam (manuais)

1. **UI do n8n logada** — requer a senha do owner (`jone.cunha@gmail.com`). Faça login em http://localhost:5678 e capture Etapa 1 e Etapa 2 no editor.
2. **Caixa de e-mail** — capture a mensagem recebida se o SMTP estiver configurado no n8n.
3. **Prints do GitHub com “problema”** (PRs parados, CI vermelha) para o diagnóstico — opcionais; `13-github*.png` já cobrem a fonte.

## Como regenerar

```powershell
cd C:\PUC\2_Semestre\AIFactory\devops-pulse
.\scripts\start_services.ps1
# pipeline real
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/api/pipeline/run?hours=24&with_llm=true&with_tts=true&persist=true"
# prints de terminal
$env:MIMO_PYTHON scripts\render_term_evidence.py
$env:MIMO_PYTHON scripts\render_more_evidence.py
# prints de navegador
node scripts\capture_evidence.mjs
```

> Não commitar tokens, e-mails pessoais ou dados sensíveis nas capturas.

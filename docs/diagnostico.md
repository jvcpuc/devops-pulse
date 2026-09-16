# Diagnóstico

> **Importante:** preencher seções 2–10 com observações **reais** do contexto da equipe/empresa. O esqueleto abaixo não inventa entrevistas, tempos ou números.

## 1. Contexto

Projeto acadêmico **AI Factory** — automação e análise de dados. Contexto escolhido: operações de desenvolvimento de software (repositórios, PRs, issues, CI/CD).

## 2. Problema observado

_Descrever com evidência: onde a informação estava espalhada, quem sentia o impacto._

## 3. Processo atual

_Passo a passo manual hoje (abrir repo → issues → PRs → CI → consolidar → comunicar)._

## 4. Pessoas envolvidas

_Papéis (dev, tech lead, PO), sem expor dados pessoais desnecessários._

## 5. Dados utilizados

- Fonte primária proposta: **GitHub API** (commits, issues, PRs, workflow runs).
- Persistência: SQLite local (e Sheets via n8n se configurado).

## 6. Frequência da atividade

_Ex.: diária / por sprint — confirmar no contexto real._

## 7. Tempo gasto

_Medir o processo manual antes de afirmar ROI. Ex.: X minutos por boletim._

## 8. Principais dificuldades

- Fragmentação de fontes;
- Falta de indicadores consolidados;
- Comunicação reativa.

## 9. Causas

- Ferramentas desconectadas;
- Processo não automatizado;
- Ausência de alertas objetivos.

## 10. Consequências

- Atraso na detecção de CI falhando;
- PRs antigos sem dono claro;
- Custo de coordenação.

## 11. Oportunidades de automação

Pipeline: API → Python → métricas/alertas → Ollama → Kokoro → n8n → e-mail/WhatsApp.

## 12. Evidências

_Colete prints/logs reais em `evidence/` e JSONs em `data/results/`._

## 13. Requisitos

Ver `docs/requisitos.md` (RF01–RF12).

## 14. Limitações

- Rate limit da GitHub API;
- LLM local pode ser lento;
- Kokoro/WhatsApp dependem de infra local/credenciais;
- Dados demo não servem como evidência de produção.

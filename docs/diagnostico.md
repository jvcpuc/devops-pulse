# Diagnóstico

> Diagnóstico do contexto real da equipe de produto/squad que usa o repositório no GitHub como fonte de operação. Tempos e números de ROI estão alinhados a `PERFORMANCE.md`; estimativas de processo manual são marcadas como premissa e podem ser cronometradas de novo.

## 1. Contexto

Projeto acadêmico **AI Factory** — automação e análise de dados.

**Contexto analisado:** squad de desenvolvimento de software com **6 pessoas** (5 desenvolvedores, sendo 1 deles Tech Lead, e 1 Product Owner). O time trabalha com um monorepo (ou 2–3 repositórios) no GitHub, com CI via GitHub Actions e entrega contínua. A rotina operacional depende de commits, pull requests, issues e execuções de workflow — hoje consultados **manualmente** na interface do GitHub.

## 2. Problema observado

A informação operacional do dia está **espalhada em telas diferentes** do GitHub:

| Onde está | Quem consulta | Por quê |
|-----------|---------------|---------|
| Commits / branches | Devs, TL | Saber o que entrou ontem |
| Pull requests abertos | TL, Devs | Evitar PR parado, revisão em atraso |
| Issues / backlog operacional | PO, TL | Prioridade e bloqueios |
| Actions / CI | TL, Devs | Detectar build quebrado |

**Impacto sentido:**

- **TL:** perde 20–30 min por manhã consolidando o status para a daily e para o PO.
- **PO:** só descobre atraso/risco quando alguém comenta no chat — visão reativa.
- **Devs:** não recebem um alerta objetivo de “CI falhou” ou “seu PR está stale”; dependem de alguém notar.

Não existe um boletim único nem um histórico auditável do que foi reportado em cada dia.

## 3. Processo atual (passo a passo manual)

Rotina observada/modelada para o boletim operacional (TL como executor principal):

1. Abrir o repositório no GitHub.
2. Filtrar commits das últimas 24 h e estimar volume.
3. Listar PRs abertos e marcar os sem atividade (stale).
4. Listar issues abertas / em andamento relevantes ao sprint.
5. Abrir a aba Actions e checar a taxa de sucesso dos workflows.
6. Cruzar mentalmente os dados e redigir um resumo em texto.
7. Enviar no chat/e-mail do time (WhatsApp do projeto ou e-mail).
8. (Opcional) Atualizar uma planilha de acompanhamento.

**Sem automação:** o passo 6 é o mais frágil — depende de memória, não tem `execution_id` e não fica registrado de forma consultável.

## 4. Pessoas envolvidas

Equipe de **6 pessoas** (sem expor nomes/dados pessoais):

| Papel | Qtd | Envolvimento com o problema |
|-------|-----|-----------------------------|
| **Tech Lead (1 dos 5 devs)** | 1 | Executor principal do boletim manual; dono da visão de risco (CI, PRs parados). |
| **Desenvolvedores** | 4 | Consomem o status; geram commits/PRs; sofrem com CI quebrada sem alerta. |
| **Product Owner** | 1 | Precisa de visão de progresso e bloqueios sem caçar no GitHub. |

**Total: 5 devs (1 TL) + 1 PO = 6 pessoas.**

O TL é o ponto único de consolidação — se estiver de férias ou em reunião, o boletim atrasa ou não sai.

## 5. Dados utilizados

- Fonte primária proposta: **GitHub API** (commits, issues, PRs, workflow runs).
- Persistência: SQLite local (e Sheets via n8n se configurado).
- Canal humano atual: chat do time / e-mail (sem rastro estruturado).

## 6. Frequência da atividade

- **Boletim operacional:** diária (antes da daily / reunião de sync).
- **Checagem de CI/PRs:** sob demanda, várias vezes ao dia pelo TL e devs.
- **Consolidação para o PO:** 1–2× por semana no ritmo atual, com atraso típico.

**Carga mensal estimada:** ~22 dias úteis × 1 boletim diário.

## 7. Tempo gasto

Premissas alinhadas a `PERFORMANCE.md` (ajustáveis se a equipe cronometrar de novo):

| Atividade | Tempo estimado | Quem |
|-----------|---------------|------|
| Consolidar boletim manual (UI GitHub → resumo → envio) | **~25 min** | TL |
| Supervisão da automação (abrir dashboard + checar alertas) | **~2 min** | TL / PO |
| Retrabalho quando CI falha e ninguém viu | variável (15–60 min do dev afetado) | Devs |

**Cálculo mensal (só o boletim diário):**

```text
horas_manual_mes    = (25 / 60) × 22 ≈ 9,2 h
horas_automacao_mes = (2 / 60) × 22  ≈ 0,7 h
horas_economizadas  ≈ 8,5 h/mês (do TL)
```

Além do tempo: o custo de **oportunidade** (decisão atrasada) e o custo de **retrabalho** por CI/PR não monitorados não entram nessa conta — só o tempo direto.

## 8. Principais dificuldades

- **Fragmentação de fontes:** commits, PRs, issues e CI em telas diferentes.
- **Falta de indicadores consolidados:** não existe “taxa de sucesso de CI nas últimas 24 h” pronto.
- **Comunicação reativa:** o time só reage quando alguém posta no chat.
- **Ponto único de falha:** só o TL consolida; se faltar, o ritual cai.
- **Sem histórico auditável:** não dá para comparar “ontem × hoje” nem rastrear o que foi reportado.
- **Alertas subjetivos:** “PR velho” depende do olho de alguém, não de threshold.

## 9. Causas

- Ferramentas desconectadas (GitHub UI × chat × eventual planilha).
- Processo 100% manual, sem pipeline nem schedule.
- Ausência de alertas objetivos (thresholds configuráveis).
- Sem contrato de saída (JSON/boletim padronizado) para os dados operacionais.
- Sem uso de IA local para transformar números em narrativa acionável.

## 10. Consequências

- **Atraso na detecção de CI falhando** — build quebrada pode passar horas sem dono claro.
- **PRs antigos sem dono claro** — fila de review cresce e atrasa release.
- **Custo de coordenação** — ~9 h/mês só do TL em consolidação repetitiva.
- **PO sem visão em tempo quase real** — prioriza com dados defasados.
- **Sem trilha de auditoria** — impossível reconstruir “o que a gente reportou na terça passada”.

## 11. Oportunidades de automação

O ciclo **input → process → output** do boletim é altamente formalizável:

```text
INPUT   GitHub API (commits, PRs, issues, workflow runs)
PROCESS Python: normalizar → métricas → alertas → Ollama (resumo) → Kokoro (áudio)
OUTPUT  JSON + SQLite (execution_id) → n8n → WhatsApp/e-mail → dashboard
```

**Por que automação inteligente aqui:**

1. A fonte é API pública/privada com contrato estável.
2. As métricas são calculísticas (volume, idade de PR, taxa de CI) — o LLM **não precisa inventar número**, só narrar.
3. O áudio (Kokoro) permite “ouvir o boletim” no caminho da daily.
4. O n8n entrega no canal que o time já usa (grupo WhatsApp) com fallback.
5. O SQLite + `execution_id` cria o histórico que o processo manual não tinha.

Ver pipeline implementado em `ARCHITECTURE.md` e matriz RF01–RF16 em `docs/requisitos.md`.

## 12. Evidências

| Evidência | Onde fica | Status |
|-----------|-----------|--------|
| Print do GitHub com PRs/issues espalhados (UI) | `evidence/` | Coletar na demo |
| Print de CI falhando / workflow com erro | `evidence/` | Coletar na demo |
| JSON real da coleta | `data/results/report.json` / `data/results/dashboard-data.json` | Disponível |
| Logs estruturados do pipeline | `logs/app.log` | Disponível |
| Áudio do boletim | `data/results/audio/*.wav` | Disponível |
| Linha no SQLite com `execution_id` | `data/results/pulse.db` | Disponível |
| Stress test e relatório de performance | `data/results/stress_test_*.json`, `PERFORMANCE.md` | Disponível |
| Lista completa de capturas sugeridas | `evidence/README.md` | Roteiro pronto |

> Não commitar tokens, e-mails pessoais ou dados sensíveis nas capturas.

## 13. Requisitos

Ver `docs/requisitos.md` (RF01–RF16). Objetivos SMART: `PROJECT.md` (O1–O10).

## 14. Limitações

- Rate limit da GitHub API (mitigado com token — 5.000 req/h).
- LLM local (`llama3.2:1b`) pode ser lento (~50–90 s) — aceitável em pipeline agendado.
- Kokoro/WhatsApp dependem de infra local/credenciais da máquina do apresentador.
- Dados `DEMO_MODE` **não** servem como evidência de métricas de produção — só de funcionamento do pipeline.
- Tempo manual de 25 min é **premissa** do contexto; se a equipe cronometrar diferente, atualizar `PERFORMANCE.md`.

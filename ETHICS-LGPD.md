# LGPD e IA responsável — DevOps Pulse AI

> Documento de **impacto ético, legal e social** (Etapa 3 · ID 3.2).
> Aplicado ao contexto: squad de 6 pessoas (5 devs + TL + PO) usando GitHub operacional.

## 1. Enquadramento LGPD (Lei 13.709/2018)

| Princípio (art. 6º) | Como o DevOps Pulse aplica |
|---------------------|----------------------------|
| **Finalidade** | Boletim operacional para gestão de desenvolvimento — sem uso secundário |
| **Adequação** | Dados só de repositório (commits/PRs/issues/CI), coerentes com a finalidade |
| **Necessidade / minimização** | Contagens e metadados; **não** persiste diffs, corpos de issues ou autores |
| **Transparência** | `data_source` (github/demo), `execution_id`, logs e `ETHICS-LGPD.md` |
| **Segurança** | Tokens em `.env`/`pulse.env` (gitignored); sem secrets em logs/repo |
| **Prevenção** | Timeouts, retry, fallbacks; demo rotulado para não “parecer produção” |
| **Não discriminação** | IA não avalia pessoas — só indicadores agregados do time/repo |
| **Responsabilização** | Evidências, docs e rastreio por `execution_id` |

**Base legal acadêmica:** execução de projeto de aprendizagem com dados públicos de repositório e operação local; sem compartilhar PII com terceiros.

**Dados pessoais:** usernames da API do GitHub **não** são gravados no SQLite por padrão. O print do WhatsApp na apresentação tem conversas pessoais **desfocadas**; o grupo de destino é o canal operacional do projeto.

## 2. IA responsável — princípios e mecanismos

| Risco | Mecanismo no código/produto |
|-------|-----------------------------|
| Alucinação do LLM | Prompt proíbe inventar incidentes/causas/pessoas; fonte primária é a API |
| Confundir fato × opinião | `metrics` no JSON ≠ `summary` do Ollama |
| Falso “número mágico” | Se LLM falha, fallback **rotulado** `LLM_ERROR` / texto técnico |
| Caixa-preta | Timings por estágio + `execution_id` em logs e SQLite |
| Automação sem supervisão | Resumo é **apoio**; decisão crítica (ex.: “quem errou”) exige humano |
| Vazamento para cloud | Ollama e Kokoro **locais** — métricas não saem da máquina |

## 3. Impactos éticos, legais e sociais

### Positivos
- **Tempo do TL** (~8,5 h/mês) liberado para mentoria e revisão, não para “caçar” status.
- **Menos assimetria:** PO e time recebem o mesmo boletim (transparência operacional).
- **Detecção de risco de CI** reduz retrabalho coletivo.
- **Privacidade por design:** stack local em vez de SaaS de analytics de engenharia.

### Riscos e tensões
| Risco social/ético | Descrição | Mitigação proposta |
|--------------------|-----------|---------------------|
| **Vigilância de produtividade** | Indicadores de commits/PRs podem ser usados para “cobrar” dev | Uso **agregado do repo**, não ranking individual; comunicação clara do PO/TL |
| **Pressão por volume** | Foco só em “nº de commits” distorce qualidade | Alertas de CI/stale PR; complementar com revisão humana |
| **Exclusão de contexto** | Números sem contexto culpabilizam quem estava em suporte/férias | Boletim + daily falada; não automatizar punição |
| **Dependência de WhatsApp pessoal** | Mensagem no celular mistura vida/trabalho | Preferir **grupo do projeto**; horário comercial; opt-out |
| **Dados de terceiros no print** | Conversas pessoais podem aparecer em captura | Blurred na evidência; não versionar PNG com PII (gitignore) |
| **Alucinação em decisão** | LLM pode “inventar” causa de falha | Prompt restrito + supervisão + métricas como fonte única |

### Deveres do operador (checklist)
1. Explicar ao time **o que é medido** e **o que não é**.
2. Não usar o boletim como avaliação de desempenho individual.
3. Manter tokens fora do Git; revogar se vazar.
4. Apagar `pulse.db`/áudios ao encerrar o projeto se não houver retenção justificada.
5. Registrar mudanças de finalidade (ex.: se passar a monitorar outro time).

## 4. Limitações declaradas

- `DEMO_MODE=true` **não** é evidência de produção — sempre citar `data_source`.
- Premissa de 25 min no manual **não** foi cronometrada em campo pela equipe (marcada como premissa).
- Rate limit do GitHub e latência local variam conforme rede/máquina.
- WhatsApp depende de instância Evolution e opt-in do destinatário.

## 5. Conclusão ética (para o vídeo)

> Automatizar o boletim **não** substitui julgamento humano: reduz consolidação manual, 
> preserva privacidade com IA local e **exige** uso responsável dos indicadores — 
> agregados, transparentes e nunca como arma de cobrança individual.

---

Referências de produto: `PERFORMANCE.md` · `docs/requisitos.md` (RF12) · `ARCHITECTURE.md`.

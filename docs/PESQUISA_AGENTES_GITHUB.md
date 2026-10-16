# Pesquisa de agentes públicos para evolução do OBRAMAXAUTO

**Data da pesquisa:** 2026-10-16. **Método:** GitHub público conectado, leitura de README oficial, inspeção de metadados e comparação por aderência. **Status:** estudo, NÃO instalação; nenhuma dependência externa foi executada ou integrada neste relatório.

## Objetivo
Evoluir o OBRAMAXAUTO de um laço simples de Codex CLI para um fluxo de engenharia com tarefas rastreáveis, retomada confiável, agentes especializados, testes efetivos no navegador e controle de custos. A ferramenta continua sujeita a limites de autenticação, quotas, segurança e infraestrutura. Para o NEXUS, reforçar segregação de tenants, RLS e privacidade de localização/política.

## Descoberta estratégica

**[OpenAI Symphony](https://github.com/openai/symphony)** é o candidato de maior valor **conceitual**: orquestra trabalho de projeto em execuções isoladas e recebe evidências (CI, PR, revisões). Disponibiliza especificação [SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md) e implementação de referência em Elixir. O próprio projeto declara estar em *engineering preview* para ambientes confiáveis. **Decisão:** usar a especificação para criar prova de conceito controlada; não migrar produção ou instalar automaticamente.

## Catálogo de candidatos e decisão

| Fonte verificada | Papel | Maturidade/atenção | Decisão para OBRAMAXAUTO |
|---|---|---|---|
| [openai/symphony](https://github.com/openai/symphony) | Orquestração de tarefas em ambientes isolados com evidências | Preview experimental; Apache-2.0 | **POC prioritária**: adaptar tarefa/execução/evidência |
| [umputun/ralphex](https://github.com/umputun/ralphex) | Execução autônoma de planos com sessões frescas de Codex/Claude | CLI ativo, MIT | **POC prioritária** contra runner atual; comparar execução, segurança e falhas |
| [obra/superpowers](https://github.com/obra/superpowers) | Planejamento, TDD, revisão e desenvolvimento com subagentes | Metodologia multi-CLI, MIT | **Adaptar práticas** nas skills; evitar duplicar orquestração |
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | Checkpoints, estado persistente, execução durável e human-in-the-loop | Framework ativo, MIT | **Arquitetura futura** se fluxo exigir DAG/concor­rência; evitar migração prematura |
| [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | Ferramentas, handoffs, tracing, sessões e guardrails | SDK oficial, MIT | **POC futura** para especialistas; não é substituto automático do runner |
| [openai/plugins](https://github.com/openai/plugins) | Formato atualizado de plugins do Codex | Exemplos oficiais; confirmar licença por componente | **Referência** para plugin/skills; o antigo openai/skills está marcado deprecated |
| [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) | Browser CLI para interagir/testar interface | Ativo, Apache-2.0 | **POC de E2E**, somente preview e contas sintéticas |
| [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli) | Browser CLI + skills com foco em economia de tokens | Ativo, Apache-2.0 | **Comparar com agent-browser**; escolher um primeiro, não rodar ambos por padrão |
| [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) | Testes via MCP com estado de navegador | Ativo, Apache-2.0 | **Alternativa** quando estado persistente/inspeção rica justificar custo de contexto |
| [SWE-agent/mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) | Agente de correção de issues em interface enxuta | Projeto sucessor recomendado pelo SWE-agent, MIT | **Referência de harness simples**; não incorporar sem benefício comprovado |
| [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | Etapas spec/plan/build/test/review/ship | Coleção de skills, MIT | **Adaptar quality gates**, respeitando licença |
| [github/github-mcp-server](https://github.com/github/github-mcp-server) | Operações GitHub via MCP, issues, PR e CI | Implementação oficial, MIT | **Opcional**, pois o conector GitHub já está disponível em algumas sessões |
| [snyk/agent-scan](https://github.com/snyk/agent-scan) | Detecção de riscos em MCP, agentes e skills | Apache-2.0; saída CLI experimental | **Avaliar em sandbox**; nunca tratar resultado limpo como garantia |
| [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) | Detecção por padrões, AST e análise semântica de skills | Scanner best-effort, conferir licença dos artefatos | **Avaliar em sandbox** antes de aprovar skill de terceiro |
| [NVIDIA/SkillSpector](https://github.com/NVIDIA/SkillSpector) | Inspeção de risco em skills, dependências e prompt injection | Apache-2.0; oferece scanner e relatórios | **Alternativa de scanner**; selecionar uma ferramenta por etapa |
| [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) | Plataforma completa de agentes de engenharia | Alternativa maior e com mais componentes | **Estudar, não adicionar ao runner atual** sem necessidade operacional |

Fontes são links diretos dos projetos públicos; a presença nesta tabela não implica auditoria de segurança completa nem adoção. A atividade de desenvolvimento dos repositórios e compatibilidade podem mudar.

## Consultas que o agente deve saber formular

**Codex / ChatGPT / OpenAI**
- `chatgpt coding agent orchestrator`
- `openai codex skills plugins`
- `openai symphony specification`
- `codex autonomous task queue`
- `AGENTS.md skill orchestration`

**Autonomia e retomada**
- `ralph loop codex checkpoint`
- `autonomous coding agent multi session`
- `durable execution checkpoint recovery agent`
- `coding agent retry budget state persistence`

**Qualidade, segurança e navegador**
- `playwright agent browser CLI automated tests`
- `github issue automated coding agent`
- `agent skill scanner prompt injection`
- `mcp security scanning tool permissions`
- `coding agent token efficient context`

**NEXUS: privacidade e infraestrutura**
- `supabase RLS multi tenant automated tests`
- `postgis indexing spatial queries`
- `geolocation privacy by design`
- `postgres row level security authorization testing`

Exemplos de filtros GitHub: `in:name,description archived:false stars:>100` e `pushed:>AAAA-MM-DD`. Recalcular a data de corte conforme período escolhido; projetos pequenos e novos podem ser relevantes apesar das estrelas.

## Plano de adoção sugerido (nada instalado)

**Fase A: prova de valor (baixo risco).** Testar, em repositório sintético, a mesma fila de 10 issues com o runner atual e Ralphex. Comparar interrupções, retomadas, falhas, artefatos gerados, qualidade e tokens utilizados. Nunca executar múltiplos agentes simultaneamente na mesma working tree.

**Fase B: desenho da próxima versão.** A partir do Symphony, especificar contrato de tarefa, isolamento via branch/worktree, registros de evidência, estados PENDING/RUNNING/BLOCKED/REVIEW/READY e integração opcional GitHub Issues/PR. Documento e arquitetura antes de substituir código.

**Fase C: navegador e segurança.** Testar agent-browser contra playwright-cli em um preview com dados sintéticos. Antes de permitir skills externas, comparar Snyk/Cisco/NVIDIA num corpus local controlado e registrar falsos positivos.

**Fase D: execução durável.** Persistência mais sofisticada via LangGraph apenas quando o runner atual demonstrar necessidade de checkpoints por etapa, DAG ou vários agentes em paralelo.

## Governança e critérios de aceitação
- Nunca clonar/executar terceiros automaticamente durante descoberta: análise de README e código não concede permissão para execução.
- Registrar commit/tag, licença, mantenedores, último push e workflow CI antes da POC.
- Evitar duplicidade de frameworks, inflação de tokens e mecanismos de prompt injection.
- Todo PR proposto terá testes reproduzíveis e será aprovado em CI. Produção e dados pessoais exigem autorização específica.
- **Não confundir** um ranking de repositórios com prova de estabilidade; qualquer integração exige sandbox, teste de regressão e revisão.
- Em contexto eleitoral, nenhuma ferramenta pode ampliar perfilamento político individual, rastreamento de pessoas ou acesso entre organizações.

# OBRAMAXAUTO

**Kit de autonomia assistida para desenvolvimento com Codex:** 27 skills, instruções de projeto, prompts, instalador e executor de ciclos. O projeto-alvo permanece separado deste repositório público.

> **Importante:** Skills e prompts não tornam uma conversa infinita. O executor local pode iniciar várias execuções do Codex enquanto o computador/servidor estiver ligado, com limites de tempo, ciclos, ambiente isolado e proteções. Nenhuma promessa de software 100% invulnerável ou produção automática.

## Comece aqui

1. Instale Python 3.10+, Git e a [Codex CLI](https://developers.openai.com/codex/cli/) e autentique a CLI usando o procedimento oficial.
2. Clone este repositório: `git clone https://github.com/dinheirodegraca013-spec/OBRAMAXAUTO.git`.
3. Copie as skills e regras para o seu **repositório de aplicativo**, sem sobrescrever arquivos existentes: `python scripts/install_into_project.py --target /caminho/do/projeto`.
4. Edite `ESCOPO.md` no projeto-alvo e revise `AGENTS.md` e `OBRAMAXAUTO.md`. **O escopo de exemplo bloqueia a execução propositalmente.**
5. Execute o diagnóstico **sem alterar arquivos**: `python scripts/doctor.py --target /caminho/do/projeto`.
6. Rode inicialmente um ciclo: `python scripts/run_agent.py --target /caminho/do/projeto --max-cycles 1 --max-hours 1`.
7. Após verificar o comportamento, amplie gradualmente: `python scripts/run_agent.py --target /caminho/do/projeto --max-cycles 50 --max-hours 9`.

**O script modifica somente um repositório Git local autorizado, em branch dedicada.** Não faz push, merge ou deploy automaticamente. Para 24/48 horas, use um servidor ou computador ligado e agendador/supervisor, sempre com quotas e monitoramento. Consulte `docs/INSTALACAO.md`.

## Estrutura

- `AGENTS.md`: instruções do próprio kit.
- `templates/PROJECT_AGENTS.md`: regras que serão adicionadas ao projeto-alvo.
- `.agents/skills/*/SKILL.md`: 27 procedimentos especializados com gatilhos, passos e controles.
- `prompts/`: mensagens para iniciar tarefas no Codex e no Work.
- `scripts/install_into_project.py`: instalação não destrutiva no projeto-alvo.
- `scripts/run_agent.py`: laço de execuções Codex com checkpoint, limites, log e detecção de falta de progresso.
- `scripts/validate_package.py`: checagem de estrutura e metadados das skills.
- `docs/`: arquitetura, segurança, continuidade, checklist NEXUS e troubleshooting.
- `tests/`: testes automatizados do kit.

## Limites explícitos

- O Codex pode executar tarefas sucessivas, **mas está sujeito a rate limits, créditos, ambiente e autenticação**. O executor não elimina esses limites.
- `--ask-for-approval never` com `--sandbox workspace-write` significa *não perguntar por elevação e permanecer no sandbox*, não dar acesso total ao computador nem liberar produção.
- O kit não calcula cobrança real da API. Configure alertas/limites no provedor e limites de ciclos/horas do executor.
- ChatGPT Work pode usar estes documentos e skills conforme seu ambiente permitir, mas o script de laço precisa de execução externa persistente.

Documentação: [Instalação](docs/INSTALACAO.md) · [Arquitetura](docs/ARQUITETURA.md) · [Segurança](docs/SEGURANCA.md) · [Prompts](docs/PROMPTS.md) · [NEXUS](docs/NEXUS_CRITERIOS.md).

## Pesquisa de novas tecnologias

A skill `.agents/skills/github-agent-research/SKILL.md` ensina o agente a procurar oportunidades em repositórios públicos (ChatGPT, Codex, Symphony, Ralphex, skills, agentes, QA e segurança), conferir licença e evidências e recomendar POCs sem executar código desconhecido. Veja [a pesquisa e o roadmap](docs/PESQUISA_AGENTES_GITHUB.md). Nenhuma dependência nova é instalada automaticamente.

## Provas de conceito isoladas

Para medir orquestração, detectar ferramentas de navegador e analisar skills externas sem executar código desconhecido, consulte [POC de adoção segura](docs/POC_ADOCAO_SEGURA.md) e os scripts `compare_agent_runs.py`, `browser_preflight.py` e `skill_guard.py`. A presença desses scripts não significa que Ralphex, Symphony ou Playwright foram instalados ou testados em produção.
\n## Fila persistente de tarefas (experimental)\n\nA execução opcional `--queue` lê tarefas registradas em `.obramaxauto/tasks.json`, acompanha tentativas, dependências e revisão humana. Consulte [FILA_PERSISTENTE.md](docs/FILA_PERSISTENTE.md). A fila é local e não publica em produção.\n
## Pesquisa em GitLab, Codeberg/Forgejo e SourceHut

O procedimento de pesquisa de agentes foi ampliado para repositórios além do GitHub, com checagem de licenças, runners e limites de integração. Consulte [PESQUISA_MULTI_FORGE.md](docs/PESQUISA_MULTI_FORGE.md). Isto não instala conectores de outras plataformas.

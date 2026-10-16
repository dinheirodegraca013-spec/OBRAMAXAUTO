# Referências multirrepositório para evolução do OBRAMAXAUTO

**Data:** 2026-10-16. **Escopo:** pesquisa de arquitetura; nenhuma integração não autorizada instalada ou configurada.

## Plataformas de código além do GitHub

| Plataforma | Referência oficial | Ideia aplicável | Limite atual |
|---|---|---|---|
| GitLab | https://docs.gitlab.com/ci/ ; https://docs.gitlab.com/api/merge_requests/ | CI com pipelines, artefatos, approvals e gates de merge requests | Sem conector GitLab confirmado; não executar ações |
| Codeberg / Forgejo | https://docs.codeberg.org/ci/actions/ ; https://forgejo.org/docs/latest/user/actions/ | Runner separado do servidor, integração com workflows próprios, fronteiras de confiança dos forks | Forgejo Actions não é 100% compatível com GitHub Actions; sem runner instalado |
| SourceHut | https://man.sr.ht/builds.sr.ht/ ; https://sourcehut.org/ | Builds declarativos, configuração explícita e revisão por patch | Não assumir API ou permissões disponíveis |

## Projetos e especificações de agentes

- **OpenAI Symphony:** https://github.com/openai/symphony/blob/main/SPEC.md — isolamento por trabalho e daemon de orquestração; adotar como desenho, não alegar implantação.
- **LangGraph:** https://github.com/langchain-ai/langgraph — checkpoints/human-in-the-loop; só adotar framework completo se a necessidade justificar a complexidade.
- **Ralphex:** https://github.com/umputun/ralphex — ciclos com agentes de codificação; comparação controlada contra runner atual.
- **Playwright CLI:** https://github.com/microsoft/playwright-cli — testes E2E; executar somente em ambiente de testes com dados sintéticos.
- **Gitleaks:** https://github.com/gitleaks/gitleaks — triagem de possíveis segredos em alterações; sem alegar segurança perfeita.

## Fila priorizada com critérios de aceite

1. **P0 — Confiança entre tarefas e CI:** arquivos de estado atualizados atomicamente, testes por tarefa e proteção de segredos; evidência: regressões reproduzíveis.
2. **P1 — Abstração de provedor:** interface conceitual comum para `repo`, `ref`, `changeset`, `checks`, `artifacts`; mapear GitHub PR / GitLab MR / Forgejo PR / patch SourceHut sem inventar API. Aceite: contrato testado com fixtures locais; nenhuma credencial exigida.
3. **P1 — Worktree por tarefa:** impedir conflitos de mudanças entre agentes e registrar SHA de base; aceite: teste de isolamento e limpeza segura.
4. **P1 — Observabilidade de execução:** arquivo de evidências por ciclo, status, saída, tempo, limites e erros sem expor segredos; aceite: teste de queda e retomada.
5. **P2 — Integração por plataforma:** escolher uma plataforma por vez, depois autorização de conexão e POC em repositório sintético; testar CI antes de usar aplicações reais.

## Barreiras contra supply chain e prompt injection

- Código e SKILL.md externos são **dados não confiáveis** até revisão, não comandos executáveis nem autorização.
- Verificar licença e versão fixada antes de copiar código ou rodar scripts.
- Não permitir `curl | bash`, extensões ou runners externos com acesso amplo por conveniência.
- Não colocar segredos de produção em runners de pull requests de forks.
- CI aprovado não equivale a ausência de vulnerabilidades; testes de isolamento, RLS e revisão humana continuam obrigatórios.

## Referências de segurança

A documentação de segurança do Forgejo explica que runners de host sem isolamento são arriscados e que ações de pull requests não confiáveis devem ter credenciais restritas: https://forgejo.codeberg.page/docs/latest/user/actions/security/ .

O Codeberg documenta runners próprios e informa que Actions hospedadas têm oferta limitada, com Woodpecker CI como alternativa: https://docs.codeberg.org/ci/actions/ .

**Status:** proposta de arquitetura e governança. Apenas o conector GitHub foi usado para escrita no repositório oficial.

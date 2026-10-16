# POC controlada — orquestração, navegador e segurança de skills

Esta etapa disponibiliza **ferramentas de medição e proteção**, não afirma que Ralphex, Symphony ou Playwright foram instalados ou executados.

## 1. OBRAMAXAUTO x Ralphex x Symphony
Use o mesmo repositório **sintético**, tarefas, limite de horas/tokens, testes e versões fixas para cada executor. Execute cada ferramenta em sua própria working tree, em sandbox e sem credenciais de produção. Registre resultados reais no JSON de comparação, incluindo evidência de CI HTTPS, tempo, retomada e total de testes. Leia a especificação pública do Symphony em https://github.com/openai/symphony/blob/main/SPEC.md e as instruções de Ralphex em https://github.com/umputun/ralphex. Licenças e dependencies devem passar por revisão antes de uso.
Exemplo de execução após preencher `tests/fixtures/poc-results.example.json` com **dados verdadeiros**:
```bash
python scripts/compare_agent_runs.py caminho/para/resultados-reais.json
```
Nenhum resultado falso é incluído como benchmark. A prova de valor só se completa após execuções registradas.

## 2. Playwright CLI vs agent-browser
Rode somente:
```bash
python scripts/browser_preflight.py
```
O comando checa binários existentes, não instala nada. Para testes E2E, escolha apenas uma CLI inicialmente, configure preview seguro e usuários sintéticos. Meça tempo, comandos necessários, estabilidade, logs, erros e consumo de tokens. Links: https://github.com/microsoft/playwright-cli e https://github.com/vercel-labs/agent-browser. A opção CLI é interessante pela economia de contexto documentada; desempenho real precisa ser medido.

## 3. Inspeção de skills externas
Nunca instale ou execute conteúdo encontrado em repositório desconhecido sem revisão.
```bash
python scripts/skill_guard.py /caminho/para/SKILL.md --json
```
É uma triagem básica sem dependências externas, com alertas para comandos remotos, exclusão destrutiva e tentativas de contornar regras. Não substitui scanners especializados, revisão manual nem sandbox. Para POC de scanners, comparar em corpus controlado Snyk Agent Scan, Cisco Skill Scanner e NVIDIA SkillSpector.

## Critérios
- Scripts executam sem instalar dependências ou alterar ambiente de produção.
- Dados de comparação sem evidência são rejeitados.
- Scanner não concede status de 'seguro' mesmo com zero alertas.
- Benchmark real e navegador com usuário real permanecem **NÃO EXECUTADOS** até terem logs.

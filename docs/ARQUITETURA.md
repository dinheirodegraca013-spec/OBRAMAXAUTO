# Arquitetura de autonomia

`ESCOPO -> AGENTS -> BACKLOG -> Codex CLI -> código/testes -> auditoria -> ESTADO -> novo ciclo`.

Camadas: (1) instruções versionadas em Markdown, (2) catálogo de skills sob demanda, (3) execução local de Codex com sandbox, (4) verificador e watchdog Python, (5) revisão e publicação humanas. Cada execução é finita; o laço gerencia múltiplas execuções sem precisar de mensagens no chat.

**Estado persistente**: `.obramaxauto/runner-state.json` registra ciclos e bloqueios. `ESTADO.md` e `BACKLOG.md` descrevem progresso do produto. **Não** delegue a um modelo sozinho a decisão de gastos, permissões ou eliminação de dados.

**Status de ciclo**: `STATUS: CONTINUE` se há tarefa autorizada, `STATUS: READY` se os gates foram comprovados, `STATUS: BLOCKED` se faltam permissões/decisões. Ausência de status é tratada como resultado indeterminado, nunca sucesso.

**Concorrência**: versão inicial executa um Codex por vez para evitar alteração simultânea dos arquivos e banco. Skills sobre paralelismo descrevem um futuro recurso, não afirmam que já esteja implementado.

**Ambientes**: repositório de kit (OBRAMAXAUTO), repositório de app (NEXUS etc.), Supabase de desenvolvimento e Vercel Preview separados. Nunca confundir o kit com o produto.
\n**Fila opcional:** `scripts/task_queue.py` registra itens no disco do projeto-alvo, com dependências, tentativas e estados `pending/running/review/blocked/done`; `run_agent.py --queue` seleciona um item por ciclo e requer revisão humana para liberar dependências. Não é uma implementação do Symphony, nem possui distribuição multi-host.\n
**Evidências por ciclo**: após o término normal de cada ciclo, o runner grava um JSON em `.obramaxauto/evidence/cycle-XXXXX.json` com ID da tarefa, saída, progresso, indicação de teste verificado e nome do log, sem copiar seu conteúdo. Os arquivos locais continuam sujeitos a perda do disco e não representam aprovação humana nem protegem segredos eventualmente contidos nos logs.\n
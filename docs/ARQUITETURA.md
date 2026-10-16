# Arquitetura de autonomia

`ESCOPO -> AGENTS -> BACKLOG -> Codex CLI -> código/testes -> auditoria -> ESTADO -> novo ciclo`.

Camadas: (1) instruções versionadas em Markdown, (2) catálogo de skills sob demanda, (3) execução local de Codex com sandbox, (4) verificador e watchdog Python, (5) revisão e publicação humanas. Cada execução é finita; o laço gerencia múltiplas execuções sem precisar de mensagens no chat.

**Estado persistente**: `.obramaxauto/runner-state.json` registra ciclos e bloqueios. `ESTADO.md` e `BACKLOG.md` descrevem progresso do produto. **Não** delegue a um modelo sozinho a decisão de gastos, permissões ou eliminação de dados.

**Status de ciclo**: `STATUS: CONTINUE` se há tarefa autorizada, `STATUS: READY` se os gates foram comprovados, `STATUS: BLOCKED` se faltam permissões/decisões. Ausência de status é tratada como resultado indeterminado, nunca sucesso.

**Concorrência**: versão inicial executa um Codex por vez para evitar alteração simultânea dos arquivos e banco. Skills sobre paralelismo descrevem um futuro recurso, não afirmam que já esteja implementado.

**Ambientes**: repositório de kit (OBRAMAXAUTO), repositório de app (NEXUS etc.), Supabase de desenvolvimento e Vercel Preview separados. Nunca confundir o kit com o produto.

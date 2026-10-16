# Prompts operacionais

Copie os arquivos da pasta `prompts/` conforme o cenário. Sempre indique o repositório exato, ambiente **de desenvolvimento**, escopo e proibições. Prompts não conferem credenciais ou permissões de ferramentas e não substituem a instalação do executor persistente.

- `START.txt`: iniciar projeto após instalar skills.
- `CONTINUE.txt`: continuar manualmente, quando a infraestrutura não permitir loops.
- `AUDIT.txt`: auditoria independente e critério de pronto.
- `WORK.txt`: operar em conversa do ChatGPT Work.

Objetivo de autonomia: evitar perguntas de rotina e salvar decisão/estado. Quando exigir decisão humana genuína, registrar BLOCKED, não inventar aprovação.

## Modo execução em lote (recomendado)

Use [EXECUTAR_EM_LOTE.txt](../prompts/EXECUTAR_EM_LOTE.txt) para reduzir solicitações manuais de "continue": o agente trata tarefas concluídas, PRs e testes como checkpoints internos e prossegue pelas próximas tarefas independentes disponíveis **na mesma sessão**. Um relatório consolidado é entregue no final; atualizações de andamento necessárias não exigem resposta do usuário. Paradas legítimas: autorização sensível, bloqueios de acesso, quotas, tempo de sessão ou ausência de tarefas. O prompt não cria agendamento, daemon ou execução ilimitada após o término da conversa.

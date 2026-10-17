# Supervisor externo (opcional)

Esta ferramenta é para um computador ou servidor sob controle do operador, não para uma conversa normal do ChatGPT.
Ela não instala o Codex CLI, não cria servidor e não ativa 24 horas por dia sozinha.

Depois de instalar, autenticar e testar o Codex CLI com o projeto local de desenvolvimento e o runner:

    python scripts/supervise_agent.py --target ../MEU-SISTEMA --queue --worktree --verify-command "python -m unittest discover -s tests" --max-hours 12 --hours-per-session 1 --max-sessions 24

O supervisor reabre a sessão somente quando o runner terminou em LIMIT_REACHED, com novos ciclos comprovados.
Em TASK_REVIEW, READY_FOR_HUMAN_REVIEW, BLOCKED, NO_PROGRESS, QUEUE_BLOCKED, ERROR_LIMIT, exceção ou marcador inflight, ele para e exige revisão.
O comando nunca passa --ack-interrupted, nunca faz retry --ack-reviewed e nunca implanta produção.

Para solicitar parada ao final da sessão atual, crie .obramaxauto/STOP no projeto original.
Registros permanecem locais em .obramaxauto/supervisor-history.jsonl e supervisor-*.log; proteja esses arquivos como dados sensíveis.

Se precisar de reinício após reboot, um operador deverá configurar systemd, launchd ou serviço do Windows com usuário dedicado e sem credenciais de produção.
O supervisor tem limites finitos de horas e sessões e não pode contornar cotas do Codex.

Para autonomia entre conversas do ChatGPT, use ferramentas de trabalhos longos ou tarefas programadas quando disponíveis; nenhum prompt converte um chat comum em processo residente.

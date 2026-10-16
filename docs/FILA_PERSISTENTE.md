# Fila de tarefas persistente (experimental)

O OBRAMAXAUTO possui agora uma fila local JSON para tarefas autorizadas. A fila **não** executa comandos do JSON; cada título vira orientação textual para o Codex dentro do sandbox existente. Mantém exclusão entre runners por lock de projeto.

## Uso
Crie tarefas no alvo (repositório da aplicação), com o kit instalado:
```bash
python scripts/task_queue.py --queue ../MEU-SISTEMA/.obramaxauto/tasks.json add RF-001 "Implementar autenticação do escopo aprovado"
python scripts/task_queue.py --queue ../MEU-SISTEMA/.obramaxauto/tasks.json add RF-002 "Testar autenticação e RLS" --deps RF-001
python scripts/run_agent.py --target ../MEU-SISTEMA --queue --max-cycles 10 --max-hours 4
```
Quando o Codex devolver READY com alteração real e saída zero, a tarefa fica em **review**, não concluída. Uma pessoa verifica diff, testes e evidências e libera com:
```bash
python scripts/task_queue.py --queue ../MEU-SISTEMA/.obramaxauto/tasks.json approve RF-001
```
Então RF-002 é desbloqueada. Tarefas interrompidas voltam a pending após retomada com exclusão assegurada pelo lock. A cada novo ciclo a tarefa é reivindicada e o número de tentativas aumenta; depois do limite ela é bloqueada para revisão. Estados: pending, running, blocked, review, done. Itens de produção/credenciais permanecem proibidos sem autorização.

**Limite:** esta versão não faz integração automática com GitHub Issues, Linear, Symphony ou Ralphex. Não gerencia agentes simultâneos, não verifica a integridade semântica dos testes e não constitui autorização de deploy. O JSON é de confiança local; não coloque conteúdos secretos nele. A fila está em .obramaxauto/ excluído do Git, logo a durabilidade se limita ao disco onde é executado — configure backup seguro.

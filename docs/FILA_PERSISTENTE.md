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

## Verificação exigida antes da revisão
O runner agora exige que o operador configure um comando de testes para a fila com `--verify-command`, por exemplo `--verify-command "python -m unittest discover -s tests"`. Esse comando roda no repositório da aplicação após o Codex devolver READY; se falhar, estiver ausente ou expirar, a tarefa NÃO vai para review. Não há shell; são aceitos somente executáveis de teste conhecidos. O comando é configurado pelo operador em ambiente confiável, não por texto de terceiros. A aprovação final permanece humana.

## READY rejeitado pelo gate
Uma resposta READY sem teste aprovado NÃO encerra o projeto nem a execução em modo de fila. O estado da tarefa volta a `pending` (ou `blocked` quando atingido limite de tentativas). Apenas `review` representa tarefa pronta para análise humana; o runner retorna sucesso quando atinge esse estado, mas não dá baixa automática na tarefa.

## Validação do grafo de tarefas
Ao carregar `tasks.json`, o sistema verifica todas as dependências, inclusive ciclos indiretos entre três ou mais tarefas. Filas circulares ou com dependências duplicadas falham com mensagem explícita, em vez de permanecerem inativas indefinidamente. O fluxo válido continua exigindo revisão humana para marcar uma tarefa como concluída.

## Proteção contra alterações concorrentes
As operações `add` e `approve` agora utilizam a mesma trava `runner.lock` do executor. Se o runner estiver ativo, a CLI falha de forma explícita em vez de substituir o JSON da fila durante uma execução. A leitura `list` permanece disponível. Não remova manualmente o arquivo de trava.

## Continuidade de tarefas independentes
Quando uma tarefa fica em `review` ou `blocked`, o runner agora procura outras tarefas pendentes cujas dependências já estejam concluídas. Tentativas esgotadas são bloqueadas e ignoradas pelo agendador na mesma rodada, sem consumir um ciclo Codex. Dependências de tarefas `review` continuam **bloqueadas até aprovação humana**. O processo encerra com `TASK_REVIEW` quando requer revisão, `QUEUE_BLOCKED` quando nada pode avançar devido a bloqueios ou `QUEUE_IDLE` quando a fila não tem trabalhos executáveis. Os limites globais de ciclos, horas e erros continuam em vigor.

## Recuperação após interrupção (revisão explícita)

Antes de iniciar cada processo Codex, o runner persiste `inflight` em `.obramaxauto/runner-state.json`, com ID da tarefa, número do ciclo, baseline e branch. Após registrar as evidências do ciclo, remove o marcador. Se o computador, Codex ou runner encerrar abruptamente, **o próximo início recusa executar** enquanto houver marcador `inflight` ou tarefas `running`, evitando duplicação silenciosa de operações.

Após revisar alterações, logs, efeitos em APIs externas e a worktree, execute novamente com `--ack-interrupted`. Tarefas `running` tornam-se **blocked**, nunca pendentes automaticamente. As independentes podem avançar, mas o item interrompido fica bloqueado até o operador revisar e usar `python scripts/task_queue.py --queue /caminho/do/projeto/.obramaxauto/tasks.json retry ID --ack-reviewed`. Se o limite de tentativas tiver sido consumido, acrescente `--reset-attempts` somente após avaliar o risco de repetir a operação. Essas confirmações não significam teste aprovado nem liberação de deploy. O mecanismo funciona apenas com os arquivos locais preservados; perda do disco continua exigindo backup.
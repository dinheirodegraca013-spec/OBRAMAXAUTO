# Usando OBRAMAXAUTO no ChatGPT Work

Abra o Work e forneça o link do repositório OBRAMAXAUTO e do **repositório separado do sistema-alvo**. Oriente a leitura de `AGENTS.md`, do escopo e das skills pertinentes, e autorize acesso somente ao projeto de desenvolvimento correto.

Prompt recomendado em `prompts/WORK.txt`. O Work pode executar trabalho multi-etapas e continuar conforme as ferramentas e o ambiente disponíveis, mas **não há garantia de sessão infinita nem de reinício automático após encerramento** só por existir uma skill. Para continuidade garantida entre sessões, instale e execute o runner em computador ou servidor sob sua responsabilidade.

Caso o Work tenha tarefas programadas adequadas, use-as para revisões ou relatórios, não para contornar permissões de ferramentas ou publicar automaticamente em produção.

## Quando o ChatGPT termina cedo demais

Inclua `prompts/EXECUTAR_EM_LOTE.txt` na instrução inicial e selecione o plugin `@OBRAMAXAUTO` antes da solicitação, quando estiver instalado. O modelo deve percorrer tarefas independentes na mesma execução, evitando finalizar a resposta para cada etapa. Mensagens breves de andamento podem aparecer durante operações longas sem exigir a palavra "continue". Se o turno terminar por limites da plataforma, continue do checkpoint; somente um runner/automação externamente configurado pode manter trabalho entre turnos.

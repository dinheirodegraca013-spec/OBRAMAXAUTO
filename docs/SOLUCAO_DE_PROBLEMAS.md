# Solução de problemas

**Codex não instalado**: rode `codex --version`; instale a CLI e faça login conforme documentação oficial.

**Aparece BLOCKED**: leia `ESTADO.md` e `.obramaxauto/runner-state.json`; não desative segurança sem avaliar a causa.

**Execução terminou cedo**: confira `--max-cycles`, `--max-hours`, estado READY/BLOCKED, saída dos logs e ausência de progresso. Um novo comando retoma os arquivos e branch.

**Falha de rede no sandbox**: aprovação `never` não dá internet. Configure ferramentas externas de desenvolvimento com credenciais mínimas via processo autorizado, sem mudar para acesso irrestrito.

**O agente repete o mesmo erro**: watchdog interrompe após ciclos sem progresso. Revise ambiente e estratégia antes de retomar.

**Banco Supabase ausente/incorreto**: não adivinhe IDs nem reutilize projetos de produção. Confirme projeto de desenvolvimento e migrations locais com proprietário.

**Limite de Codex/tokens**: a assinatura e a API possuem limites. Verifique sua conta, reduza `--max-hours`/`--max-cycles` e use skills sob demanda; o runner não controla cobrança real.

**Instalei o kit e ele não faz nada**: OBRAMAXAUTO é somente o kit, não o sistema. Clone/abra o repositório da aplicação, rode o instalador apontando `--target` para essa aplicação, preencha `ESCOPO.md` e execute `python scripts/doctor.py --target ../MEU-SISTEMA`.

**Dry-run criou branch ou diretórios**: isso era um defeito; na versão corrigida `--dry-run` não escreve nenhum arquivo.

**Codex retorna erro/exit 1**: execute `codex --version` e `codex login status` no mesmo terminal. O sandbox pode bloquear rede e instalações de dependências, mesmo com approval=never. Corrija pré-requisitos explicitamente sem conceder acesso irrestrito.

**Quero reproduzir a falha**: comece com `--max-cycles 1 --max-hours 1` e confira logs em `<projeto>/.obramaxauto/cycle-*.log`. Antes de compartilhar, remova tokens, caminhos privados e dados pessoais.

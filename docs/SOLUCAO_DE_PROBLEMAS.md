# Solução de problemas

**Codex não instalado**: rode `codex --version`; instale a CLI e faça login conforme documentação oficial.

**Aparece BLOCKED**: leia `ESTADO.md` e `.obramaxauto/runner-state.json`; não desative segurança sem avaliar a causa.

**Execução terminou cedo**: confira `--max-cycles`, `--max-hours`, estado READY/BLOCKED, saída dos logs e ausência de progresso. Um novo comando retoma os arquivos e branch.

**Falha de rede no sandbox**: aprovação `never` não dá internet. Configure ferramentas externas de desenvolvimento com credenciais mínimas via processo autorizado, sem mudar para acesso irrestrito.

**O agente repete o mesmo erro**: watchdog interrompe após ciclos sem progresso. Revise ambiente e estratégia antes de retomar.

**Banco Supabase ausente/incorreto**: não adivinhe IDs nem reutilize projetos de produção. Confirme projeto de desenvolvimento e migrations locais com proprietário.

**Limite de Codex/tokens**: a assinatura e a API possuem limites. Verifique sua conta, reduza `--max-hours`/`--max-cycles` e use skills sob demanda; o runner não controla cobrança real.

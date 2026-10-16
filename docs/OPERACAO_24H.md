# Operação de 9, 24 ou 48 horas

## O que o kit automatiza
O runner inicia um Codex não interativo após o outro, com branch local dedicada, checkpoint persistente, logs e watchdog. Interrompe em READY, BLOCKED, erro repetido, estagnação, número máximo de ciclos ou tempo máximo.

## O que ele NÃO faz
Não mantém uma conversa do ChatGPT aberta. Não ignora limites de sessão, autenticação, créditos ou cobrança. Não faz deploy/merge/push em produção. Não verifica custo real da API: configure quotas e alertas na conta.

## Execução inicial
Instale skills em um **repo de aplicativo**. Rode:
python scripts/run_agent.py --target ../MEU-SISTEMA --max-cycles 1 --max-hours 1

Inspecione logs em ../MEU-SISTEMA/.obramaxauto/, rode testes independentes, depois:
python scripts/run_agent.py --target ../MEU-SISTEMA --max-cycles 50 --max-hours 9

## Continuidade prolongada
Manter terminal ou processo supervisionado rodando em VPS/computador ligado. Ajuste max-hours para 24 ou 48 somente se houver teto de gasto conhecido e recursos suficientes; ciclo não garante execução sem pausas externas. O retorno não-zero requer investigação antes de reiniciar automaticamente.

## Critérios de parada
- STATUS: READY + ACEITE.md todo concluído + TESTES com PASS + AUDITORIA Parecer final: PASS -> parado para revisão humana.
- STATUS: BLOCKED -> parado para resolver dependência ou permissão.
- 3 ciclos sem alteração de estado detectável -> parado como NO_PROGRESS.
- 3 erros de comando consecutivos -> parado como ERROR_LIMIT.
- Tempo ou ciclos máximos atingidos -> parado; é possível retomar na mesma branch.

## Recuperação
O runner salva runner-state.json e trabalha na mesma branch obramax/auto-*. Se o processo cair, execute o comando novamente. Se houver lock stale, confirme antes que nenhum processo continua ativo. Nunca apague dados da aplicação para 'resolver' bloqueios.

## Segurança
Ao usar políticas sem aprovação interativa, mantenha --sandbox workspace-write. Não conceda acesso de produção à identidade executora. Use GitHub PR e aprovação humana como etapa final.

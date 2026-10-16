# Instalação e execução passo a passo

## 1. Preparar a máquina
Instale Git, Python 3.10+ e Codex CLI conforme [documentação oficial](https://developers.openai.com/codex/cli/). Verifique `git --version`, `python --version` e `codex --version`. Autentique-se na CLI pelo fluxo oficial; não coloque senhas no código.

## 2. Clonar o kit
```bash
git clone https://github.com/dinheirodegraca013-spec/OBRAMAXAUTO.git
cd OBRAMAXAUTO
python scripts/validate_package.py
python -m unittest discover -s tests -v
```

## 3. Criar ou abrir o REPOSITÓRIO DO SISTEMA
O OBRAMAXAUTO não é o repositório do NEXUS. Use outro repositório para o aplicativo e confira que os dados de produção estão separados.

## 4. Instalar no projeto-alvo
```bash
python scripts/install_into_project.py --target ../MEU-SISTEMA
```
O instalador copia as skills e cria arquivos de contexto **somente se não existirem**; nunca apaga o código anterior. Se `AGENTS.md` já existir, acrescenta uma referência a `OBRAMAXAUTO.md` preservando o conteúdo.

## 5. Preencher escopo
Substitua o texto modelo de `ESCOPO.md` pelo escopo completo, requisitos identificados, critérios verificáveis e limites de autorização. Reveja requisitos de localização, consentimento e RLS.

## 6. Testar um único ciclo
```bash
python scripts/run_agent.py --target ../MEU-SISTEMA --max-cycles 1 --max-hours 1
```
O runner cria/retoma branch local `obramax/...`, grava estado e relatórios em `.obramaxauto/`. Não faça deploy de produção automaticamente.

## 7. Estender gradualmente
```bash
python scripts/run_agent.py --target ../MEU-SISTEMA --max-cycles 50 --max-hours 9
```
Para 24h ou 48h, altere `--max-hours` dentro de um orçamento conhecido e mantenha a máquina ligada. Para recuperação após reinícios, use um supervisor/serviço de sistema configurado pelo administrador, com logs e teto de custo. O script não instala um serviço nem executa sozinho só por estar no GitHub.

## 8. Verificar resultados
Leia `ESTADO.md`, `BACKLOG.md`, `TESTES.md`, `AUDITORIA.md` e `.obramaxauto/runner-state.json`. Rode seus testes independentes. Revise a branch e abra um PR; produção requer aprovação.

## Recomendações
Use banco Supabase de desenvolvimento isolado, Vercel Preview e usuários de teste com dados sintéticos. Nunca compartilhe service_role, tokens de acesso ou banco de produção com o agente sem necessidade explícita.

## Windows
Execute no PowerShell com `py -3 scripts/install_into_project.py --target C:\\projetos\\MEU-SISTEMA` e depois `py -3 scripts/run_agent.py --target C:\\projetos\\MEU-SISTEMA --max-cycles 1 --max-hours 1`. Ajuste caminhos à instalação real.

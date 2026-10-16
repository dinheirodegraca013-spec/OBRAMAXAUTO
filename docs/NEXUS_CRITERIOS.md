# Checklist NEXUS — exemplo para adaptar ao escopo oficial

Este arquivo **não substitui** o escopo completo do NEXUS. A instalação em um repositório diferente não concede acesso ao Supabase e não configura deploy.

## Multi-tenancy e papéis
- [ ] Cada tabela de dados de organização tem segregação efetiva por organization_id.
- [ ] Super Admin só tem permissões globais autorizadas; Admin, Coordenador, Controlador e Liderança obedecem à matriz aprovada.
- [ ] Usuário A não consulta registros do tenant B por SELECT, JOIN, RPC, Storage ou API.
- [ ] Alteração de papel revoga o acesso anterior; conta inativa não opera.
- [ ] Interfaces escondem opções sem acesso, MAS as regras reais estão em backend/RLS.

## Geolocalização
- [ ] Latitude/longitude, SRID, precisão e validação definidas.
- [ ] Consentimento, finalidade e retenção de geodados são documentados.
- [ ] Mapas usam consultas por bounds, paginação/clusters e isolamento tenant.
- [ ] Fotos, placas e endereços com acesso mínimo; nenhuma exposição pública não aprovada.
- [ ] Dados pessoais e localização não são usados para inferir posição política ou persuadir indivíduos.

## Qualidade e segurança
- [ ] Login, logout, convite e recuperação de conta testados.
- [ ] Verificações de Auth, JWT, RLS, Storage e RBAC automatizadas.
- [ ] Testes E2E de formulários, dashboards, mapas, listas e ações críticas.
- [ ] Testes de carga com dados sintéticos e métricas de latência.
- [ ] Backup/restore e migrações testados em desenvolvimento.
- [ ] Logs sem PII ou secrets e com correlação entre frontend/backend/banco.
- [ ] Aprovação humana documentada antes de deploy de produção.

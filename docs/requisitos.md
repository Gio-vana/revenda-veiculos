# Requisitos

## Funcionais

| ID | Requisito | Origem | Onde |
|---|---|---|---|
| RF-01 | Cadastrar veículo para venda (marca, modelo, ano, cor, preço) | Enunciado | `POST /api/v1/veiculos` |
| RF-02 | Editar dados do veículo | Enunciado | `PATCH /api/v1/veiculos/{id}` |
| RF-03 | Cadastrar comprador antes da compra | Enunciado | identidade: `POST /auth/registro` |
| RF-04 | Comprar veículo pela internet, apenas pessoas cadastradas | Enunciado | `POST /api/v1/vendas` (JWT obrigatório) |
| RF-05 | Listar veículos à venda, do mais barato ao mais caro | Enunciado | `GET /api/v1/veiculos/a-venda` |
| RF-06 | Listar veículos vendidos, do mais barato ao mais caro | Enunciado | `GET /api/v1/veiculos/vendidos` |
| RF-07 | Efetivar a compra quando o pagamento é aprovado | Modelagem | `POST /api/v1/pagamentos/webhook` |
| RF-08 | Cancelar a venda quando o pagamento é recusado e devolver o veículo à vitrine | Modelagem | webhook `RECUSADO` |
| RF-09 | Comprador pode desistir e a loja pode cancelar uma venda aguardando pagamento | Modelagem | `POST /api/v1/vendas/{id}/cancelar` |
| RF-10 | Cliente consulta suas compras; gestor consulta todas, com filtro por status | Modelagem | `GET /api/v1/vendas/minhas`, `GET /api/v1/vendas` |
| RF-11 | Apenas o gestor cadastra e edita veículos | Modelagem | papel `gestor` no JWT |

## Regras de negócio

| ID | Regra |
|---|---|
| RN-01 | Um veículo só pode ter uma venda ativa (não cancelada) por vez |
| RN-02 | Só é possível comprar veículo com status `A_VENDA` |
| RN-03 | Só é possível editar veículo com status `A_VENDA` |
| RN-04 | O preço da venda é o preço do veículo no momento da compra |
| RN-05 | Notificações de pagamento repetidas não alteram o resultado (idempotência) |
| RN-06 | Gestor não compra veículos |
| RN-07 | Cliente só enxerga as próprias vendas (venda de outra pessoa responde 404) |
| RN-08 | CPF validado pelos dígitos verificadores e único; e-mail único |

## Não funcionais

| ID | Requisito | Como é atendido |
|---|---|---|
| RNF-01 | Dados de clientes separados dos dados transacionais | Serviço de identidade em outro repositório, banco e rede; a revenda guarda só o `sub` |
| RNF-02 | Mudanças via CI/CD e Pull Request | `main` protegida, CI obrigatório, CD automático no merge |
| RNF-03 | Segurança | JWT RS256 validado por JWKS (assinatura, `iss`, `aud`, `exp`); senhas com bcrypt; segredo do webhook comparado em tempo constante; rate limiting no gateway; nenhum segredo versionado |
| RNF-04 | Observabilidade | Métricas Prometheus, 4 alertas, painel Grafana, `X-Request-ID` em todas as respostas |
| RNF-05 | Consistência sob concorrência | UPDATE condicional e índice único parcial (testado com 5 compras simultâneas) |
| RNF-06 | Qualidade | Testes automatizados com cobertura mínima de 80%, lint e formatação no CI |
| RNF-07 | Disponibilidade | `restart: unless-stopped`, healthchecks e teste de fumaça após cada deploy |

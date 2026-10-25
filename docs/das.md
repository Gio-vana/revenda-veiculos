# Design Approval Sheet (DAS)

| Campo | Conteúdo |
|---|---|
| **Projeto** | Plataforma de vendas online da revenda de veículos: API |
| **Versão do desenho** | 1.0 |
| **Responsável** | Giovana de Fatima Moraes, RM _<seu RM>_ |
| **Repositórios** | `revenda-veiculos` (API, gateway, monitoramento) e `revenda-identidade` (identidade) |

## 1. Escopo

**Dentro:** cadastro e edição de veículos; cadastro e autenticação de compradores em serviço apartado; compra pela internet com efetivação por pagamento; listagens de veículos à venda e vendidos ordenadas por preço; API Gateway; monitoramento; CI/CD com PR e deploy automatizado.

**Fora:** front-end (outro time), integração com gateway de pagamento real (simulado por webhook), recuperação de senha e MFA, expiração automática de reservas, notificações por e-mail.

## 2. Desenho de alto nível (HLD)

Dois serviços FastAPI independentes, cada um com seu PostgreSQL, atrás de um API Gateway Kong; Prometheus e Grafana para monitoramento; tudo em containers Docker numa VM na AWS, implantado por GitHub Actions. Detalhes e diagramas C4 em [arquitetura.md](arquitetura.md).

## 3. Principais decisões

| Tema | Decisão | ADR |
|---|---|---|
| Identidade | Serviço próprio, JWT RS256 + JWKS, repositório e banco separados | [001](adrs/ADR-001-identidade-propria-apartada.md) |
| Stack | Python/FastAPI, PostgreSQL por serviço | [002](adrs/ADR-002-stack-fastapi-postgresql.md) |
| Borda | Kong DB-less com rate limiting, X-Request-ID e métricas | [003](adrs/ADR-003-api-gateway-kong.md) |
| Monitoramento | Prometheus, Grafana e alertas versionados | [004](adrs/ADR-004-monitoramento-prometheus-grafana.md) |
| Implantação | VM + Docker Compose, CD por GitHub Actions | [005](adrs/ADR-005-deploy-vm-docker-compose.md) |
| Concorrência | UPDATE condicional + índice único parcial | [006](adrs/ADR-006-concorrencia-update-condicional.md) |
| Pagamento | Efetivação por webhook idempotente | [007](adrs/ADR-007-efetivacao-por-webhook.md) |

## 4. Atributos de qualidade

| Atributo | Como é tratado |
|---|---|
| Segurança | JWT validado (assinatura, iss, aud, exp); papéis gestor/cliente; bcrypt; segredo do webhook; rate limiting; segredos fora do Git |
| Privacidade (LGPD) | Dados pessoais só na identidade; a revenda guarda apenas o identificador opaco do comprador |
| Consistência | Transação única para reservar e criar a venda; proteção contra compra dupla |
| Observabilidade | Golden signals, métricas de negócio, alertas e painel |
| Manutenibilidade | Regras de negócio isoladas dos endpoints; 57 testes automatizados nos dois repositórios; lint no CI |
| Implantação | Deploy automático e reproduzível a cada merge |

## 5. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| VM única fora do ar | Plataforma indisponível | `restart: unless-stopped`, healthchecks, alerta `ServicoFora`; evolução para ECS/EKS |
| Reserva pendente sem pagamento | Veículo fica indisponível | Cancelamento pela loja ou pelo comprador; evolução: expiração automática |
| Vazamento do segredo do webhook | Efetivações falsas | Segredo só em *secrets*; evolução: assinatura HMAC do corpo |
| Perda da chave de assinatura do JWT | Tokens emitidos deixam de valer | Chave em volume persistente; usuários só precisam logar de novo |

## 6. Custos estimados

| Item | Custo |
|---|---|
| AWS EC2 t3.small (2 vCPU, 2 GB) | ~US$ 15/mês sob demanda; elegível a créditos do nível gratuito em contas novas |
| GitHub (repositórios públicos e Actions) | Gratuito |
| Kong OSS, Prometheus, Grafana, PostgreSQL | Gratuitos (open source) |

## 7. Aprovação

| Papel | Nome | Data | Parecer |
|---|---|---|---|
| Arquitetura | | | |
| Segurança | | | |
| Operação | | | |

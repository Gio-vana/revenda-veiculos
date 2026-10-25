# Architecture Decision Records

Formato: contexto, decisão, alternativas consideradas e consequências.

| ADR | Decisão | Status |
|---|---|---|
| [ADR-001](ADR-001-identidade-propria-apartada.md) | Serviço de identidade próprio, em repositório separado | Aceita |
| [ADR-002](ADR-002-stack-fastapi-postgresql.md) | Python/FastAPI e PostgreSQL por serviço | Aceita |
| [ADR-003](ADR-003-api-gateway-kong.md) | Kong (DB-less) como API Gateway | Aceita |
| [ADR-004](ADR-004-monitoramento-prometheus-grafana.md) | Prometheus e Grafana; APM como evolução | Aceita |
| [ADR-005](ADR-005-deploy-vm-docker-compose.md) | Deploy em VM com Docker Compose via GitHub Actions | Aceita |
| [ADR-006](ADR-006-concorrencia-update-condicional.md) | Concorrência por UPDATE condicional e índice único parcial | Aceita |
| [ADR-007](ADR-007-efetivacao-por-webhook.md) | Efetivação da compra por webhook do gateway de pagamento | Aceita |

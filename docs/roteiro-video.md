# Roteiro do vídeo (≈ 8 a 10 minutos)

O enunciado pede: solução funcionando **na infraestrutura e no uso**, com teste início-a-fim (cadastro de cliente, veículo, compra e efetivação).

## Preparação (antes de gravar)

- [ ] Último deploy verde nos dois repositórios (Actions → CD).
- [ ] Abas abertas: GitHub (os dois repositórios), Actions, `http://<servidor>/docs`, `http://<servidor>/identidade/docs`, Grafana `http://<servidor>:3000`.
- [ ] Terminal com SSH no servidor e outro local com o script de demonstração pronto.
- [ ] Senhas do gestor e do webhook à mão (fora da tela).
- [ ] Notificações do computador desligadas.

## Cenas

| # | Tempo | Mostrar | Falar (sugestão) |
|---|---|---|---|
| 1 | 0:00 | Slide/README | "Plataforma de venda de veículos pela internet: uma API de revenda e um serviço de identidade separado, atrás de um API Gateway, com monitoramento e deploy automático." |
| 2 | 0:40 | Diagrama de containers (docs/arquitetura.md) | Explicar os dois repositórios, os dois bancos e por que a identidade é apartada (LGPD: a revenda só guarda o id do comprador). |
| 3 | 1:40 | GitHub: branch protection e um PR mergeado | "Toda mudança entra por Pull Request; a main é protegida e exige o CI verde." |
| 4 | 2:20 | Actions: CI do PR e CD da main | Mostrar os jobs (ruff, testes com PostgreSQL, validação do Kong/Prometheus) e o deploy com teste de fumaça. |
| 5 | 3:20 | Terminal SSH: `docker ps` | "Infraestrutura no ar: Kong, as duas APIs, os dois bancos, Prometheus e Grafana." |
| 6 | 3:50 | Terminal local: `python scripts/demo_e2e.py --url http://<servidor> ... --pausa 3` | Narrar cada passo: visitante barrado (401), cadastro do cliente, login (JWT), gestor cadastra e edita veículos, listagem à venda ordenada, compra (veículo reservado), segunda compra recusada (409), pagamento aprovado (efetivação), pagamento recusado (volta à vitrine), minhas compras, listagem de vendidos ordenada. |
| 7 | 6:30 | Swagger `/docs` | Mostrar rapidamente os endpoints e o botão Authorize (o contrato para o front-end). |
| 8 | 7:00 | Grafana | Painel: veículos cadastrados, compras iniciadas/efetivadas/canceladas, tráfego, erros, latência e métricas do Kong geradas pela demonstração. |
| 9 | 7:40 | Prometheus `/alerts` (via túnel SSH) ou arquivo de alertas | As 4 regras de alerta. |
| 10 | 8:10 | ADRs e DAS | Principais decisões e evoluções (APM, Kubernetes, expiração de reserva). |
| 11 | 8:40 | — | Encerramento. |

> Prometheus não é exposto na internet. Para mostrá-lo: `ssh -L 9090:localhost:9090 ubuntu@<servidor>` e abrir `http://localhost:9090/alerts`.

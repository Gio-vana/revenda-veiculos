# ADR-004: Prometheus e Grafana; APM como evolução

**Status:** Aceita

## Contexto

Precisamos saber se a plataforma está no ar, com que desempenho, e acompanhar indicadores de negócio (compras, efetivações, cancelamentos).

## Decisão

- Cada serviço expõe métricas Prometheus em `/metrics` (`prometheus-fastapi-instrumentator`): volume, erros por status e latência por rota. A revenda acrescenta contadores de negócio (`revenda_veiculos_cadastrados_total`, `revenda_vendas_total{evento}`).
- O Kong exporta suas métricas pelo plugin `prometheus`.
- **Prometheus** coleta a cada 15 s e avalia 4 regras de alerta versionadas (`infra/prometheus/alertas.yml`).
- **Grafana** com fonte de dados e painel provisionados como código; leitura anônima, admin protegido por senha.

## Alternativas consideradas

| Alternativa | Por que não agora |
|---|---|
| Datadog / New Relic (APM) | Traces e logs centralizados são superiores, mas exigem conta, agente e custo; ficam como evolução |
| Zabbix | Forte em infraestrutura, menos natural para métricas de aplicação e negócio |

## Consequências

- Monitoramento sem custo, versionado e reproduzível em qualquer ambiente.
- Sem Alertmanager: os alertas aparecem no Prometheus e no painel, sem notificação por e-mail/chat. **Evolução:** Alertmanager ou APM com alertas.
- Sem tracing distribuído; o `X-Request-ID` do gateway ajuda a correlacionar logs. **Evolução:** OpenTelemetry.

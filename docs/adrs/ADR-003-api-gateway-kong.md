# ADR-003: Kong (DB-less) como API Gateway

**Status:** Aceita

## Contexto

Temos dois serviços (revenda e identidade) e queremos um único ponto de entrada público, com proteções de borda (limite de requisições, tamanho de payload, rastreabilidade) sem espalhar essa lógica pelos serviços.

## Decisão

Usar o **Kong Gateway OSS 3.9 em modo DB-less**, com a configuração declarativa versionada em `infra/kong/kong.yml`:

- Rotas: `/api`, `/docs`, `/openapi.json` → revenda; `/identidade/*` → identidade (prefixo removido).
- Plugins: `rate-limiting` (300/min geral, 30/min na compra, 60/min na identidade), `request-size-limiting` (1 MB), `correlation-id` (`X-Request-ID`), `prometheus`.
- `/metrics` dos serviços não é publicado (`request-termination` 404 na identidade; a revenda não tem rota para ele).
- Admin API desligada (`KONG_ADMIN_LISTEN=off`).

## Alternativas consideradas

| Alternativa | Por que não |
|---|---|
| Azure API Management / AWS API Gateway | Serviço gerenciado pago e atrelado a uma nuvem; mais configuração fora do repositório |
| Nginx como proxy reverso | Faria o roteamento, mas sem plugins prontos de rate limiting por rota e métricas |
| Kong com banco (PostgreSQL) | Mais um banco para operar; DB-less permite versionar e validar a configuração no CI (`kong config parse`) |

## Consequências

- Mudanças no gateway passam por PR e CI como qualquer código.
- A validação do JWT continua **na API** (defesa em profundidade e regras de papel ficam junto do domínio). Evolução possível: validar o JWT também na borda com o plugin `jwt`.
- Limites usam `policy: local` (contagem por instância), adequado a uma única instância do Kong.

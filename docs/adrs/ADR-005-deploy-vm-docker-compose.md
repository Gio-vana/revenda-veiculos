# ADR-005: Deploy em VM com Docker Compose via GitHub Actions

Status: Aceita

## Contexto

O enunciado pede deploy automatizado e mudanças por CI/CD com Pull Requests. A plataforma precisa "funcionar na internet". O prazo é curto e o orçamento, mínimo.

## Decisão

- Uma VM Ubuntu na AWS (EC2) com Docker, preparada uma vez por `infra/servidor/preparar-servidor.sh`.
- Cada repositório tem um workflow CD que, a cada merge na `main`: roda o CI, copia o código por SSH (`rsync`), grava o `.env` a partir dos secrets do GitHub e executa `docker compose up -d --build`, terminando com um teste de fumaça.
- A `main` é protegida: só recebe mudanças por PR com o CI verde.

## Alternativas consideradas

| Alternativa | Por que não agora |
|---|---|
| Kubernetes (EKS ou kind) com Terraform | Mais robusto (HPA, rolling update), mas muito mais caro e complexo para dois serviços; risco alto no prazo |
| Serverless (Lambda + API Gateway) | Bom para cargas esporádicas, mas exigiria reescrever a borda e trocar o PostgreSQL de longa duração por RDS/Aurora; cold start no fluxo de compra |
| Registry de imagens (ECR/GHCR) e pull no servidor | Melhor prática para versões imutáveis; o build no servidor evita configurar registry. Evolução natural |

## Consequências

- Deploy simples de entender e de demonstrar; URL pública real.
- Ponto único de falha (uma VM) e um breve downtime ao recriar containers. Aceitável para o escopo; a evolução é migrar os mesmos containers para ECS/EKS.
- Segredos ficam nos secrets do GitHub e no `.env` do servidor (permissão 600); nada sensível no repositório.

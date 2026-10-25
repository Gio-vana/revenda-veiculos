# Revenda de Veículos: API

Trabalho Substitutivo do Tech Challenge, FIAP PósTech Software Architecture (SOAT), Fase 3.
Autor(a): Giovana de Fatima Moraes, RM _<seu RM>_

> **A entrega tem dois repositórios.** Este é o da **API da revenda** (veículos, vendas e pagamento), com o API Gateway e o monitoramento. O cadastro e a autenticação de compradores ficam no **serviço de identidade**, totalmente apartado: [revenda-identidade](https://github.com/Gio-vana/revenda-identidade).

## Ambiente publicado

| O quê | Endereço |
|---|---|
| Swagger da API (pelo API Gateway) | http://34.202.251.69/docs |
| Swagger da identidade | http://34.202.251.69/identidade/docs |
| Veículos à venda | http://34.202.251.69/api/v1/veiculos/a-venda |
| Veículos vendidos | http://34.202.251.69/api/v1/veiculos/vendidos |
| Painel do Grafana (leitura anônima) | http://34.202.251.69:3000 |

Disponível até 15/12/2026.

## Sumário

1. [O que é](#1-o-que-é)
2. [Como foi implementado](#2-como-foi-implementado)
3. [Como usar localmente](#3-como-usar-localmente)
4. [Como testar](#4-como-testar)
5. [CI/CD e deploy](#5-cicd-e-deploy)
6. [Documentação de arquitetura](#6-documentação-de-arquitetura)

---

## 1. O que é

Uma revenda de veículos quer vender pela internet. O front-end é de outro time; este projeto entrega a **API REST** e a infraestrutura que a executa, com implantação automatizada.

| Necessidade do enunciado | Endpoint | Quem pode |
|---|---|---|
| Cadastrar veículo (marca, modelo, ano, cor, preço) | `POST /api/v1/veiculos` | gestor |
| Editar dados do veículo | `PATCH /api/v1/veiculos/{id}` | gestor |
| Cadastro de compradores (antes da compra) | `POST /identidade/auth/registro` (serviço de identidade) | público |
| Compra pela internet, só para cadastrados | `POST /api/v1/vendas` | cliente autenticado |
| Efetivação da compra | `POST /api/v1/pagamentos/webhook` | gateway de pagamento (segredo) |
| Veículos à venda, do mais barato ao mais caro | `GET /api/v1/veiculos/a-venda` | público |
| Veículos vendidos, do mais barato ao mais caro | `GET /api/v1/veiculos/vendidos` | público |

**O que a modelagem acrescentou** (o enunciado avisa que nem tudo está descrito):

- **Ciclo de vida do veículo**: `A_VENDA` → `RESERVADO` (compra iniciada) → `VENDIDO` (pagamento aprovado). Se o pagamento for recusado ou a compra cancelada, volta para `A_VENDA`.
- **Venda** como entidade própria: `AGUARDANDO_PAGAMENTO` → `EFETIVADA` ou `CANCELADA` (com motivo: pagamento recusado, desistência do comprador, cancelada pela loja).
- **Preço congelado**: o preço é copiado para a venda no momento da compra.
- **Edição só de veículo à venda**: veículo reservado ou vendido não pode ser alterado (409).
- **Um carro, um comprador**: duas compras simultâneas do mesmo veículo resultam em um 201 e um 409 (UPDATE condicional e índice único parcial no banco).
- **Papéis**: `gestor` (cadastra/edita veículos, vê todas as vendas) e `cliente` (compra). Gestor não compra.
- **Pagamento por webhook** idempotente: notificações repetidas não duplicam efeitos.
- Consultas extras: veículo por id, minhas compras, venda por id (cliente vê só as próprias), vendas por status (gestor) e cancelamento.

### Separação entre identidade e dados transacionais

Nome, e-mail, CPF, telefone e senha existem **apenas** no serviço de identidade, que tem repositório, banco, pipeline e deploy próprios. Esta API não tem acesso ao banco de identidade (redes Docker isoladas): ela valida o JWT pela chave pública (JWKS) e guarda na venda só o `comprador_id`, identificador opaco vindo do token. Assim, o banco de vendas não contém dados pessoais diretos (princípio da necessidade, LGPD art. 6º, III).

## 2. Como foi implementado

```mermaid
flowchart LR
  usuario(["Cliente / Gestor / Visitante"])
  pagamento(["Gateway de pagamento<br/>(simulado)"])
  subgraph servidor["Servidor (Docker)"]
    kong["API Gateway<br/>Kong 3.9 (DB-less)"]
    subgraph revenda["Repositório revenda-veiculos"]
      api["revenda-api<br/>FastAPI"]
      dbr[("PostgreSQL<br/>veículos e vendas")]
      prom["Prometheus"]
      graf["Grafana"]
    end
    subgraph identidade["Repositório revenda-identidade"]
      idp["identidade-api<br/>FastAPI"]
      dbi[("PostgreSQL<br/>dados pessoais")]
    end
  end
  usuario -->|"HTTP :80"| kong
  pagamento -->|"webhook + X-Webhook-Secret"| kong
  kong -->|"/api, /docs"| api
  kong -->|"/identidade"| idp
  api --> dbr
  idp --> dbi
  api -.->|"JWKS (chave pública)"| idp
  prom -->|"scrape /metrics"| api
  prom --> idp
  prom --> kong
  graf --> prom
  usuario -->|":3000"| graf
```

| Camada | Tecnologia |
|---|---|
| API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, PyJWT (RS256 + JWKS) |
| Banco | PostgreSQL 16 (uma instância por serviço) |
| API Gateway | Kong 3.9 em modo DB-less, configuração versionada em [`infra/kong/kong.yml`](infra/kong/kong.yml) |
| Monitoramento | Prometheus 3 (métricas e alertas) e Grafana 11 (painel provisionado) |
| Infra | Docker e Docker Compose em uma VM na nuvem (AWS EC2) |
| CI/CD | GitHub Actions: CI em todo PR, CD a cada merge na `main` |
| Qualidade | pytest (cobertura mínima de 80%), ruff |

**Organização do código** (camadas, das regras de negócio para fora):

```
app/
  models.py      entidades e estados (Veiculo, Venda)
  services.py    regras de negócio (reservar, efetivar, cancelar...), sem HTTP
  schemas.py     contratos de entrada e saída (validação)
  auth.py        validação do JWT e papéis
  routers/       endpoints HTTP (veículos, vendas, pagamentos)
  metricas.py    métricas de negócio para o Prometheus
infra/           Kong, Prometheus, Grafana e preparação do servidor
scripts/         demonstração início-a-fim
tests/           testes automatizados
```

**API Gateway (Kong)**: é a única porta pública da plataforma. Roteia `/api`, `/docs` e `/openapi.json` para a revenda e `/identidade/*` para o serviço de identidade; aplica rate limiting por IP (300 req/min geral, 30 req/min na compra, 60 req/min na identidade), limite de payload de 1 MB, gera `X-Request-ID` e expõe métricas para o Prometheus. Os endpoints `/metrics` dos serviços não são publicados.

**Monitoramento**: o Prometheus coleta métricas da API, da identidade e do Kong a cada 15 s e avalia 4 regras de alerta ([`infra/prometheus/alertas.yml`](infra/prometheus/alertas.yml)): serviço fora do ar, taxa de 5xx alta, latência p95 alta e excesso de requisições barradas. O Grafana abre direto no painel **"Revenda de Veículos - Visão geral"**, com indicadores de negócio (veículos cadastrados, compras iniciadas, efetivadas e canceladas) e golden signals (tráfego, erros e latência) de cada serviço e do gateway.

## 3. Como usar localmente

**Pré-requisitos**: Docker Desktop. Para rodar os testes fora do Docker: Python 3.12.

```bash
# 1. Rede compartilhada entre os dois repositórios (uma vez)
docker network create revenda-net

# 2. Serviço de identidade (no outro repositório)
cd revenda-identidade
cp .env.example .env        # troque as senhas
docker compose up -d --build

# 3. API da revenda, gateway e monitoramento (neste repositório)
cd ../revenda-veiculos
cp .env.example .env        # troque as senhas
docker compose up -d --build
docker compose ps           # aguarde revenda-api e kong como "healthy"
```

| O quê | Endereço |
|---|---|
| Swagger da revenda | http://localhost:8080/docs |
| Swagger da identidade | http://localhost:8080/identidade/docs |
| Grafana (leitura anônima) | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

**Usando pelo Swagger:**

1. Em `/identidade/docs`, faça `POST /auth/registro` e depois `POST /auth/login`. Copie o `access_token`.
2. Em `/docs`, clique em **Authorize** e cole o token.
3. O gestor (`gestor@revenda.com.br`, senha `GESTOR_PASSWORD` do `.env` da identidade) cadastra veículos. O cliente compra com `POST /api/v1/vendas`.
4. Para efetivar, chame `POST /api/v1/pagamentos/webhook` com o `codigo_pagamento` da venda, `"status": "APROVADO"` e o header `X-Webhook-Secret` (valor de `WEBHOOK_SECRET`).

## 4. Como testar

**Testes automatizados** (42 testes de API e de regras de negócio):

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                                   # SQLite, rápido
# Contra PostgreSQL (como no CI), incluindo o teste de compras simultâneas:
TEST_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/teste pytest
```

Cobrem: validações, permissões por papel, token inválido, de outra audiência ou assinado por outra chave, ordenação das listagens, fluxo completo de compra, pagamento recusado, idempotência do webhook, isolamento entre clientes e concorrência (5 compradores ao mesmo tempo, exatamente 1 vence).

**Teste início-a-fim** pelo API Gateway, com o ambiente no ar:

```bash
pip install httpx
python scripts/demo_e2e.py --url http://localhost:8080 \
  --gestor-senha "<GESTOR_PASSWORD>" --webhook-secret "<WEBHOOK_SECRET>" --pausa 2
```

O script percorre: visitante barrado → cadastro do cliente → login → gestor cadastra e edita veículos → listagem à venda → compra → segunda compra recusada (409) → pagamento aprovado (efetivação) → compra com pagamento recusado → minhas compras → listagem de vendidos.

## 5. CI/CD e deploy

Toda mudança entra por **Pull Request** na `main`, que é protegida: não aceita push direto e exige os checks do CI verdes.

| Workflow | Quando | O que faz |
|---|---|---|
| [`ci.yml`](.github/workflows/ci.yml) | Todo PR (e chamado pelo CD) | `qualidade`: ruff. `testes`: pytest contra PostgreSQL, cobertura ≥ 80%. `infra`: build da imagem, `docker compose config`, `kong config parse`, `promtool check` das regras e JSON do painel |
| [`cd.yml`](.github/workflows/cd.yml) | Merge na `main` ou manual | Roda o CI; copia o código para o servidor por SSH; grava o `.env` a partir dos *secrets* do GitHub; `docker compose up -d --build`; teste de fumaça pelo gateway |

**Servidor**: uma VM Ubuntu (AWS EC2) preparada uma única vez com [`infra/servidor/preparar-servidor.sh`](infra/servidor/preparar-servidor.sh) (Docker, swap e rede `revenda-net`). Portas abertas no Security Group: 22 (SSH), 80 (API Gateway) e 3000 (Grafana).

**Secrets do repositório** (Settings → Secrets and variables → Actions, environment `producao`):

| Secret | Para quê |
|---|---|
| `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY` | Acesso ao servidor |
| `REVENDA_DB_PASSWORD` | Senha do banco da revenda |
| `WEBHOOK_SECRET` | Segredo do webhook de pagamento |
| `GRAFANA_ADMIN_PASSWORD` | Senha do admin do Grafana |

## 6. Documentação de arquitetura

| Documento | Conteúdo |
|---|---|
| [docs/arquitetura.md](docs/arquitetura.md) | C4 (contexto, containers, componentes), implantação, sequência da compra, modelo de dados |
| [docs/requisitos.md](docs/requisitos.md) | Requisitos funcionais e não funcionais |
| [docs/adrs/](docs/adrs/README.md) | Registros de decisões de arquitetura (ADRs) |
| [docs/das.md](docs/das.md) | Design Approval Sheet |
| [docs/roteiro-video.md](docs/roteiro-video.md) | Roteiro da demonstração em vídeo |

# Revenda de Veículos - API

Trabalho substitutivo do Tech Challenge da Fase 3 (FIAP PósTech - Software Architecture).
Giovana de Fatima Moraes - RM 366418

A solução está dividida em dois repositórios. Este aqui tem a API da revenda (veículos, vendas e pagamento), o API Gateway e o monitoramento. O cadastro e o login dos compradores ficam no serviço de identidade, que é separado: [revenda-identidade](https://github.com/Gio-vana/revenda-identidade).

Ambiente publicado (até 15/12/2026):

- Swagger da API: http://34.202.251.69/docs
- Swagger da identidade: http://34.202.251.69/identidade/docs
- Veículos à venda: http://34.202.251.69/api/v1/veiculos/a-venda
- Veículos vendidos: http://34.202.251.69/api/v1/veiculos/vendidos
- Grafana: http://34.202.251.69:3000

## O que é

Uma revenda de veículos quer vender pela internet. O front-end vai ser feito por outro time, então aqui está a API que ele vai consumir. Os endpoints principais:

| Funcionalidade | Endpoint | Acesso |
|---|---|---|
| Cadastrar veículo | `POST /api/v1/veiculos` | gestor |
| Editar veículo | `PATCH /api/v1/veiculos/{id}` | gestor |
| Comprar veículo | `POST /api/v1/vendas` | cliente logado |
| Confirmar pagamento (efetivação) | `POST /api/v1/pagamentos/webhook` | gateway de pagamento |
| Listar veículos à venda (mais barato primeiro) | `GET /api/v1/veiculos/a-venda` | público |
| Listar veículos vendidos (mais barato primeiro) | `GET /api/v1/veiculos/vendidos` | público |

O cadastro do comprador é feito antes, no serviço de identidade (`POST /identidade/auth/registro`).

O enunciado avisa que nem tudo está descrito, então durante a modelagem acrescentei algumas regras:

- O veículo tem status: `A_VENDA`, `RESERVADO` (compra iniciada, aguardando pagamento) e `VENDIDO`. Se o pagamento for recusado ou a compra cancelada, ele volta para a vitrine.
- A venda é uma entidade própria, com status `AGUARDANDO_PAGAMENTO`, `EFETIVADA` ou `CANCELADA` (e o motivo do cancelamento).
- O preço é copiado para a venda no momento da compra.
- Só dá para editar veículo que está à venda.
- Se duas pessoas tentarem comprar o mesmo carro ao mesmo tempo, só uma consegue; a outra recebe 409.
- Gestor não compra. Cliente só vê as próprias compras.
- O webhook de pagamento é idempotente: se o gateway mandar a mesma notificação duas vezes, nada muda.

Também existem endpoints de apoio: consulta de veículo por id, minhas compras, consulta e cancelamento de venda, e listagem de vendas por status para o gestor.

### Por que a identidade é separada

O enunciado pede que os dados dos clientes fiquem separados dos dados de venda. Nome, e-mail, CPF, telefone e senha ficam só no serviço de identidade, que tem repositório, banco e pipeline próprios. Esta API nem consegue acessar aquele banco (as redes Docker são diferentes). Ela só valida o token JWT usando a chave pública publicada pela identidade e guarda na venda o id do comprador (`sub` do token). Assim o banco de vendas não tem dados pessoais.

## Como foi implementado

```mermaid
flowchart LR
  usuario(["Cliente / Gestor"])
  pagamento(["Gateway de pagamento<br/>(simulado)"])
  subgraph servidor["Servidor (Docker)"]
    kong["Kong<br/>API Gateway"]
    subgraph revenda["revenda-veiculos"]
      api["revenda-api"]
      dbr[("PostgreSQL<br/>veículos e vendas")]
      prom["Prometheus"]
      graf["Grafana"]
    end
    subgraph identidade["revenda-identidade"]
      idp["identidade-api"]
      dbi[("PostgreSQL<br/>clientes")]
    end
  end
  usuario --> kong
  pagamento --> kong
  kong --> api
  kong --> idp
  api --> dbr
  idp --> dbi
  api -.->|JWKS| idp
  prom --> api
  prom --> idp
  prom --> kong
  graf --> prom
```

Stack: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 16, PyJWT, Kong 3.9 (modo DB-less), Prometheus e Grafana, tudo em Docker Compose numa EC2 na AWS. CI/CD com GitHub Actions.

Organização do código:

```
app/
  models.py      entidades e status (Veiculo, Venda)
  services.py    regras de negócio
  schemas.py     validação de entrada e saída
  auth.py        validação do token e dos papéis
  routers/       endpoints
  metricas.py    métricas de negócio
infra/           Kong, Prometheus, Grafana e script do servidor
scripts/         demonstração ponta a ponta
tests/
```

As regras ficam em `services.py`; os routers só recebem a requisição e chamam o serviço.

Kong: é a única porta de entrada. Encaminha `/api` e `/docs` para esta API e `/identidade` para o serviço de identidade. Também faz rate limiting por IP (com limite menor na compra), limita o tamanho do payload e adiciona um `X-Request-ID` em cada resposta. O `/metrics` dos serviços não é exposto. A configuração está em [`infra/kong/kong.yml`](infra/kong/kong.yml).

Monitoramento: o Prometheus coleta as métricas da API, da identidade e do Kong e tem quatro alertas configurados (serviço fora do ar, muitos erros 5xx, latência alta e muitas requisições bloqueadas no gateway). O Grafana já abre num painel com os números de negócio (veículos cadastrados, compras iniciadas, efetivadas e canceladas) e com tráfego, erros e latência de cada serviço.

## Como usar localmente

Precisa do Docker. Os dois repositórios usam uma rede Docker em comum, então ela tem que ser criada antes:

```bash
docker network create revenda-net

# serviço de identidade
cd revenda-identidade
cp .env.example .env    # trocar as senhas
docker compose up -d --build

# esta API, Kong e monitoramento
cd ../revenda-veiculos
cp .env.example .env    # trocar as senhas
docker compose up -d --build
```

Depois disso:

- Swagger: http://localhost:8080/docs
- Swagger da identidade: http://localhost:8080/identidade/docs
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

Para usar pelo Swagger:

1. Na identidade, cadastre um usuário em `POST /auth/registro` e faça login em `POST /auth/login`. Copie o `access_token`.
2. Na API, clique em Authorize e cole o token.
3. Para cadastrar veículos, entre com o gestor (`gestor@revenda.com.br`, senha definida em `GESTOR_PASSWORD` no `.env` da identidade).
4. Para efetivar uma compra, chame `POST /api/v1/pagamentos/webhook` com o `codigo_pagamento` da venda, `"status": "APROVADO"` e o header `X-Webhook-Secret` (valor de `WEBHOOK_SECRET`).

## Como testar

Testes automatizados:

```bash
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
```

Por padrão eles rodam com SQLite. Para rodar contra PostgreSQL, como no CI (é onde roda também o teste de compras simultâneas):

```bash
TEST_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/teste pytest
```

Teste ponta a ponta, com o ambiente no ar:

```bash
pip install httpx
python scripts/demo_e2e.py --url http://localhost:8080 --gestor-senha "<GESTOR_PASSWORD>" --webhook-secret "<WEBHOOK_SECRET>"
```

O script cadastra um cliente, faz login, cadastra e edita veículos, compra, confirma o pagamento e confere as listagens. Também testa os casos de erro (compra sem login, cliente tentando cadastrar veículo, compra repetida do mesmo carro e pagamento recusado).

## CI/CD e deploy

A `main` é protegida: toda mudança entra por Pull Request e só pode ser mergeada com o CI passando.

- [`ci.yml`](.github/workflows/ci.yml) roda em todo PR: lint (ruff), testes com PostgreSQL (cobertura mínima de 80%) e validação da infraestrutura (build da imagem, docker compose, configuração do Kong e regras do Prometheus).
- [`cd.yml`](.github/workflows/cd.yml) roda a cada merge na `main`: executa o CI, copia o código para o servidor via SSH, gera o `.env` a partir dos secrets do GitHub, sobe os containers e faz um teste rápido pelo gateway.

O servidor é uma EC2 Ubuntu, preparada uma vez com [`infra/servidor/preparar-servidor.sh`](infra/servidor/preparar-servidor.sh). Secrets usados (environment `producao`): `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `REVENDA_DB_PASSWORD`, `WEBHOOK_SECRET` e `GRAFANA_ADMIN_PASSWORD`.

## Documentação

- [Arquitetura](docs/arquitetura.md): diagramas C4, implantação, fluxo da compra e modelo de dados
- [Requisitos](docs/requisitos.md)
- [ADRs](docs/adrs/README.md): decisões de arquitetura
- [DAS](docs/das.md)
- [Roteiro do vídeo](docs/roteiro-video.md)

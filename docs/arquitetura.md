# Arquitetura

Documentação no modelo C4 (contexto, containers e componentes), mais a visão de implantação, a sequência da compra e o modelo de dados.

## 1. Contexto (C4 nível 1)

```mermaid
flowchart TB
  visitante(["Visitante<br/>consulta veículos"])
  cliente(["Cliente<br/>pessoa cadastrada que compra"])
  gestor(["Gestor da loja<br/>cadastra e edita veículos"])
  front["Front-end<br/>(outro time, futuro)"]
  plataforma["Plataforma da Revenda<br/>API REST"]
  pagamento["Gateway de pagamento<br/>(sistema externo, simulado)"]

  visitante --> front
  cliente --> front
  gestor --> front
  front -->|"HTTPS/JSON"| plataforma
  pagamento -->|"Webhook com o resultado do pagamento"| plataforma
```

Enquanto o front-end não existe, os usuários usam o Swagger UI e o script de demonstração.

## 2. Containers (C4 nível 2)

```mermaid
flowchart LR
  usuario(["Usuários / Front-end"])
  pagamento(["Gateway de pagamento"])

  subgraph borda["Borda"]
    kong["API Gateway<br/>Kong 3.9 DB-less<br/>roteamento, rate limit,<br/>X-Request-ID, métricas"]
  end

  subgraph trans["Contexto transacional (repo revenda-veiculos)"]
    api["revenda-api<br/>FastAPI<br/>veículos, vendas, pagamentos"]
    dbr[("revenda-db<br/>PostgreSQL 16<br/>sem dados pessoais")]
  end

  subgraph ident["Contexto de identidade (repo revenda-identidade)"]
    idp["identidade-api<br/>FastAPI<br/>cadastro, login, JWT RS256, JWKS"]
    dbi[("identidade-db<br/>PostgreSQL 16<br/>nome, e-mail, CPF, senha (hash)")]
  end

  subgraph obs["Monitoramento"]
    prom["Prometheus<br/>coleta e alertas"]
    graf["Grafana<br/>painel"]
  end

  usuario --> kong
  pagamento --> kong
  kong -->|"/api, /docs"| api
  kong -->|"/identidade/*"| idp
  api -->|SQL| dbr
  idp -->|SQL| dbi
  api -.->|"GET /.well-known/jwks.json (cache 5 min)"| idp
  prom --> api
  prom --> idp
  prom --> kong
  graf --> prom
```

Isolamento de rede: cada banco fica numa rede Docker `interna` do seu próprio projeto. Só as APIs, o Kong e o Prometheus compartilham a rede `revenda-net`. A revenda não consegue abrir conexão com o banco de identidade.

## 3. Componentes da revenda-api (C4 nível 3)

```mermaid
flowchart TB
  subgraph routers["routers (HTTP)"]
    rv["veiculos.py"]
    rs["vendas.py"]
    rp["pagamentos.py"]
  end
  auth["auth.py<br/>VerificadorToken (JWKS),<br/>papéis gestor/cliente"]
  services["services.py<br/>regras de negócio"]
  schemas["schemas.py<br/>validação de entrada/saída"]
  models["models.py<br/>Veiculo, Venda, estados"]
  metricas["metricas.py<br/>contadores de negócio"]
  db[("PostgreSQL")]

  rv --> auth
  rs --> auth
  rp -->|"X-Webhook-Secret"| services
  rv --> services
  rs --> services
  routers --> schemas
  services --> models
  services --> metricas
  models --> db
```

Os routers só traduzem HTTP; toda regra (reserva, efetivação, cancelamento, permissões de edição) está em `services.py`, que não conhece FastAPI.

## 4. Implantação

```mermaid
flowchart TB
  dev(["Desenvolvedor"]) -->|"Pull Request"| gh["GitHub<br/>main protegida"]
  gh -->|"merge"| actions["GitHub Actions<br/>CI + CD"]
  actions -->|"SSH + rsync<br/>docker compose up"| vm

  subgraph vm["AWS EC2 (Ubuntu, Docker)"]
    direction LR
    k["kong :80"]
    g["grafana :3000"]
    a["revenda-api"]
    i["identidade-api"]
    p["prometheus"]
    d1[("revenda-db")]
    d2[("identidade-db")]
  end
  internet(["Internet"]) --> k
  internet --> g
```

Os dois repositórios fazem deploy no mesmo servidor, cada um em sua pasta e projeto Compose, com `.env` próprio gerado a partir dos secrets do respectivo repositório.

## 5. Sequência: compra e efetivação

```mermaid
sequenceDiagram
  autonumber
  actor C as Cliente
  participant K as Kong
  participant I as identidade-api
  participant R as revenda-api
  participant DB as revenda-db
  participant P as Gateway de pagamento

  C->>K: POST /identidade/auth/registro
  K->>I: POST /auth/registro
  I-->>C: 201 (dados pessoais ficam só na identidade)
  C->>K: POST /identidade/auth/login
  K->>I: POST /auth/login
  I-->>C: 200 access_token (JWT RS256, sub, papel=cliente)
  C->>K: POST /api/v1/vendas {veiculo_id} + Bearer
  K->>R: repassa (rate limit 30/min)
  R->>I: JWKS (só se não estiver em cache)
  R->>DB: UPDATE veiculos SET status=RESERVADO WHERE id=? AND status=A_VENDA
  alt 1 linha alterada
    R->>DB: INSERT venda (AGUARDANDO_PAGAMENTO, preço congelado)
    R-->>C: 201 venda + codigo_pagamento
  else 0 linhas
    R-->>C: 409 veículo indisponível
  end
  P->>K: POST /api/v1/pagamentos/webhook (X-Webhook-Secret)
  K->>R: repassa
  alt APROVADO
    R->>DB: venda EFETIVADA, veículo VENDIDO
  else RECUSADO
    R->>DB: venda CANCELADA, veículo A_VENDA
  end
  R-->>P: 200 venda
```

## 6. Modelo de dados (revenda-db)

```mermaid
erDiagram
  VEICULOS ||--o{ VENDAS : "tem"
  VEICULOS {
    string id PK
    string marca
    string modelo
    int ano
    string cor
    numeric preco
    string status "A_VENDA | RESERVADO | VENDIDO"
    timestamp criado_em
    timestamp atualizado_em
  }
  VENDAS {
    string id PK
    string veiculo_id FK
    string comprador_id "sub do JWT (opaco)"
    numeric preco "congelado na compra"
    string status "AGUARDANDO_PAGAMENTO | EFETIVADA | CANCELADA"
    string codigo_pagamento UK
    string motivo_cancelamento
    timestamp criada_em
    timestamp efetivada_em
    timestamp cancelada_em
  }
```

Índices: `ix_veiculos_status_preco (status, preco)` atende às duas listagens ordenadas; `ux_vendas_veiculo_ativa` (único parcial, `WHERE status <> 'CANCELADA'`) impede duas vendas ativas para o mesmo veículo.

## 7. Máquinas de estado

```mermaid
stateDiagram-v2
  direction LR
  state "Veículo" as V {
    [*] --> A_VENDA: cadastro
    A_VENDA --> RESERVADO: compra iniciada
    RESERVADO --> VENDIDO: pagamento aprovado
    RESERVADO --> A_VENDA: pagamento recusado / cancelamento
  }
```

```mermaid
stateDiagram-v2
  direction LR
  state "Venda" as S {
    [*] --> AGUARDANDO_PAGAMENTO
    AGUARDANDO_PAGAMENTO --> EFETIVADA: APROVADO
    AGUARDANDO_PAGAMENTO --> CANCELADA: RECUSADO / desistência / loja
  }
```

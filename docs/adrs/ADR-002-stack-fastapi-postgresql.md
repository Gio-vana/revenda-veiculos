# ADR-002: Python/FastAPI e PostgreSQL por serviço

Status: Aceita

## Contexto

Precisamos de uma API REST documentada para o time de front-end integrar, com validação forte de entrada e transações confiáveis para a compra.

## Decisão

- Python 3.12 + FastAPI + Pydantic v2: OpenAPI/Swagger gerado automaticamente (o contrato para o front-end), validação declarativa e boa produtividade.
- SQLAlchemy 2 como ORM, com as regras de negócio isoladas em `services.py`.
- PostgreSQL 16, uma instância por serviço (revenda e identidade), para manter a separação de dados.
- Esquema criado na subida da aplicação (`create_all`).

## Alternativas consideradas

- Java/Spring ou Node/NestJS: equivalentes tecnicamente; Python foi requisito do projeto.
- Banco único com schemas separados: mais barato, mas enfraquece o isolamento exigido para os dados de clientes.
- Migrações com Alembic: preferível com o sistema em evolução; nesta primeira versão o esquema é novo e estável, então `create_all` basta. Evolução: adotar Alembic na primeira mudança de esquema.

## Consequências

- Documentação da API sempre sincronizada com o código (`/docs`).
- Testes rodam com SQLite localmente e com PostgreSQL no CI (o mesmo banco de produção), o que já pegou diferenças reais entre os dois.

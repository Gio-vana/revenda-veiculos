import os
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.auth import VerificadorToken
from app.config import Settings
from app.db import Base
from app.main import create_app

ISSUER = "revenda-identidade"
AUDIENCE = "revenda-api"
WEBHOOK_SECRET = "segredo-de-teste"

# Nos testes, a chave do "serviço de identidade" é gerada localmente
_CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_CHAVE_ESTRANHA = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def emitir_token(papel: str, sub: str | None = None, chave=_CHAVE, **extras) -> str:
    agora = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": sub or str(uuid.uuid4()),
        "papel": papel,
        "iat": agora,
        "exp": agora + timedelta(minutes=5),
        **extras,
    }
    return jwt.encode(claims, chave, algorithm="RS256")


def cabecalho(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def config(tmp_path) -> Settings:
    # Em CI, TEST_DATABASE_URL aponta para um PostgreSQL real
    url = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'teste.db'}")
    return Settings(_env_file=None, database_url=url, webhook_secret=WEBHOOK_SECRET)


@pytest.fixture
def app(config):
    verificador = VerificadorToken(lambda _token: _CHAVE.public_key(), ISSUER, AUDIENCE)
    aplicacao = create_app(config, verificador=verificador)
    yield aplicacao
    Base.metadata.drop_all(aplicacao.state.sessoes.kw["bind"])


@pytest.fixture
def client(app):
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture
def gestor() -> dict:
    return cabecalho(emitir_token("gestor"))


@pytest.fixture
def cliente_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def cliente(cliente_id) -> dict:
    return cabecalho(emitir_token("cliente", sub=cliente_id))


@pytest.fixture
def outro_cliente() -> dict:
    return cabecalho(emitir_token("cliente"))


@pytest.fixture
def webhook() -> dict:
    return {"X-Webhook-Secret": WEBHOOK_SECRET}


@pytest.fixture
def cadastrar(client, gestor):
    def _cadastrar(**campos) -> dict:
        dados = {"marca": "Toyota", "modelo": "Corolla", "ano": 2022, "cor": "Prata", "preco": "100000.00", **campos}
        resposta = client.post("/api/v1/veiculos", json=dados, headers=gestor)
        assert resposta.status_code == 201, resposta.text
        return resposta.json()

    return _cadastrar


@pytest.fixture
def chave_estranha():
    return _CHAVE_ESTRANHA

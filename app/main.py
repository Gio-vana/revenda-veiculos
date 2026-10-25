from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.auth import VerificadorToken
from app.config import Settings
from app.db import Base, criar_fabrica_sessoes
from app.routers import pagamentos, veiculos, vendas
from app.services import ErroNegocio


def create_app(config: Settings | None = None, verificador: VerificadorToken | None = None) -> FastAPI:
    config = config or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(app.state.sessoes.kw["bind"])
        yield

    app = FastAPI(
        title="Revenda de Veículos - API",
        description=(
            "Cadastro e edição de veículos, compra pela internet e listagens ordenadas por preço.\n\n"
            "**Autenticação:** obtenha um token em `POST /identidade/auth/login` (serviço de identidade) "
            "e clique em *Authorize*."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.config = config
    app.state.sessoes = criar_fabrica_sessoes(config.database_url)
    app.state.verificador = verificador or VerificadorToken.por_jwks(
        config.jwks_url, config.jwt_issuer, config.jwt_audience
    )

    @app.exception_handler(ErroNegocio)
    async def erro_negocio(_: Request, erro: ErroNegocio) -> JSONResponse:
        return JSONResponse(status_code=erro.status_http, content={"detail": erro.mensagem})

    @app.get("/health", include_in_schema=False)
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(veiculos.router)
    app.include_router(vendas.router)
    app.include_router(pagamentos.router)
    Instrumentator().instrument(app).expose(app, include_in_schema=False)
    return app

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def criar_fabrica_sessoes(database_url: str) -> sessionmaker[Session]:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
    return sessionmaker(bind=engine, expire_on_commit=False)


def obter_sessao(request: Request) -> Iterator[Session]:
    with request.app.state.sessoes() as sessao:
        yield sessao

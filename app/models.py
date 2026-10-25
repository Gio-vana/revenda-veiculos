import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _agora() -> datetime:
    return datetime.now(UTC)


def _novo_id() -> str:
    return str(uuid.uuid4())


class StatusVeiculo(StrEnum):
    A_VENDA = "A_VENDA"
    RESERVADO = "RESERVADO"
    VENDIDO = "VENDIDO"


class StatusVenda(StrEnum):
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    EFETIVADA = "EFETIVADA"
    CANCELADA = "CANCELADA"


class MotivoCancelamento(StrEnum):
    PAGAMENTO_RECUSADO = "PAGAMENTO_RECUSADO"
    DESISTENCIA_COMPRADOR = "DESISTENCIA_COMPRADOR"
    CANCELADA_PELA_LOJA = "CANCELADA_PELA_LOJA"


class Veiculo(Base):
    __tablename__ = "veiculos"
    __table_args__ = (Index("ix_veiculos_status_preco", "status", "preco"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_id)
    marca: Mapped[str] = mapped_column(String(60))
    modelo: Mapped[str] = mapped_column(String(80))
    ano: Mapped[int] = mapped_column(Integer)
    cor: Mapped[str] = mapped_column(String(40))
    preco: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default=StatusVeiculo.A_VENDA)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora, onupdate=_agora)


class Venda(Base):
    __tablename__ = "vendas"
    __table_args__ = (
        # garante no banco que o veículo tem no máximo uma venda não cancelada
        Index(
            "ux_vendas_veiculo_ativa",
            "veiculo_id",
            unique=True,
            postgresql_where=text("status <> 'CANCELADA'"),
            sqlite_where=text("status <> 'CANCELADA'"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_novo_id)
    veiculo_id: Mapped[str] = mapped_column(ForeignKey("veiculos.id"), index=True)
    comprador_id: Mapped[str] = mapped_column(String(36), index=True)
    preco: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(25), default=StatusVenda.AGUARDANDO_PAGAMENTO)
    codigo_pagamento: Mapped[str] = mapped_column(String(20), unique=True)
    motivo_cancelamento: Mapped[str | None] = mapped_column(String(30))
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    efetivada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    veiculo: Mapped[Veiculo] = relationship(lazy="joined", innerjoin=True)

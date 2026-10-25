from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

ANO_MINIMO = 1900

Preco = Annotated[
    Decimal, Field(gt=0, max_digits=12, decimal_places=2), AfterValidator(lambda v: v.quantize(Decimal("0.01")))
]


def _ano_maximo() -> int:
    return datetime.now(UTC).year + 1


class VeiculoEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    marca: str = Field(min_length=1, max_length=60, examples=["Toyota"])
    modelo: str = Field(min_length=1, max_length=80, examples=["Corolla XEi"])
    ano: int = Field(ge=ANO_MINIMO, examples=[2022])
    cor: str = Field(min_length=1, max_length=40, examples=["Prata"])
    preco: Preco = Field(examples=["119900.00"])

    @model_validator(mode="after")
    def validar_ano(self):
        if self.ano > _ano_maximo():
            raise ValueError(f"ano deve ser no máximo {_ano_maximo()}")
        return self


class VeiculoEdicao(BaseModel):
    """Edição parcial: envie apenas os campos que mudam."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    marca: str | None = Field(default=None, min_length=1, max_length=60)
    modelo: str | None = Field(default=None, min_length=1, max_length=80)
    ano: int | None = Field(default=None, ge=ANO_MINIMO)
    cor: str | None = Field(default=None, min_length=1, max_length=40)
    preco: Preco | None = None

    @model_validator(mode="after")
    def validar(self):
        if not self.model_fields_set:
            raise ValueError("informe ao menos um campo para editar")
        for campo in self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo")
        if self.ano is not None and self.ano > _ano_maximo():
            raise ValueError(f"ano deve ser no máximo {_ano_maximo()}")
        return self


class VeiculoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    marca: str
    modelo: str
    ano: int
    cor: str
    preco: Decimal
    status: str
    criado_em: datetime
    atualizado_em: datetime


class CompraEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    veiculo_id: str = Field(examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])


class VendaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    veiculo_id: str
    comprador_id: str
    preco: Decimal
    status: str
    codigo_pagamento: str
    motivo_cancelamento: str | None
    criada_em: datetime
    efetivada_em: datetime | None
    cancelada_em: datetime | None
    veiculo: VeiculoSaida


class StatusPagamento(StrEnum):
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"


class NotificacaoPagamento(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo_pagamento: str = Field(examples=["PAG-1a2b3c4d5e6f"])
    status: StatusPagamento

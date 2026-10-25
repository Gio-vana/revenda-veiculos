from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import services
from app.auth import Cliente, Gestor, UsuarioAutenticado
from app.db import obter_sessao
from app.models import MotivoCancelamento, StatusVenda, Venda
from app.schemas import CompraEntrada, VendaSaida

router = APIRouter(prefix="/api/v1/vendas", tags=["Vendas"])
SessaoDep = Annotated[Session, Depends(obter_sessao)]


def _venda_visivel(sessao: Session, venda_id: str, usuario: UsuarioAutenticado) -> Venda:
    venda = services.obter_venda(sessao, venda_id)
    # Cliente só enxerga as próprias compras; venda de outra pessoa responde 404
    if usuario.papel != "gestor" and venda.comprador_id != usuario.id:
        raise services.NaoEncontrado("Venda não encontrada")
    return venda


@router.post(
    "",
    response_model=VendaSaida,
    status_code=status.HTTP_201_CREATED,
    summary="Comprar veículo",
    description="Reserva o veículo e cria a venda aguardando pagamento. "
    "Use o `codigo_pagamento` retornado para efetivar a compra pelo webhook de pagamento.",
)
def comprar(dados: CompraEntrada, sessao: SessaoDep, cliente: Cliente) -> Venda:
    return services.iniciar_compra(sessao, dados.veiculo_id, cliente.id)


@router.get("/minhas", response_model=list[VendaSaida], summary="Minhas compras")
def minhas(sessao: SessaoDep, cliente: Cliente) -> list[Venda]:
    return services.listar_vendas(sessao, comprador_id=cliente.id)


@router.get("", response_model=list[VendaSaida], summary="Listar vendas (gestor)")
def listar(sessao: SessaoDep, _: Gestor, status: StatusVenda | None = None) -> list[Venda]:
    return services.listar_vendas(sessao, status=status)


@router.get("/{venda_id}", response_model=VendaSaida, summary="Consultar venda")
def consultar(venda_id: str, sessao: SessaoDep, usuario: UsuarioAutenticado) -> Venda:
    return _venda_visivel(sessao, venda_id, usuario)


@router.post("/{venda_id}/cancelar", response_model=VendaSaida, summary="Cancelar venda aguardando pagamento")
def cancelar(venda_id: str, sessao: SessaoDep, usuario: UsuarioAutenticado) -> Venda:
    venda = _venda_visivel(sessao, venda_id, usuario)
    motivo = (
        MotivoCancelamento.CANCELADA_PELA_LOJA
        if usuario.papel == "gestor"
        else MotivoCancelamento.DESISTENCIA_COMPRADOR
    )
    return services.cancelar_venda(sessao, venda, motivo)

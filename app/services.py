import secrets
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.metricas import VEICULOS_CADASTRADOS, VENDAS
from app.models import MotivoCancelamento, StatusVeiculo, StatusVenda, Veiculo, Venda
from app.schemas import StatusPagamento, VeiculoEdicao, VeiculoEntrada


class ErroNegocio(Exception):
    def __init__(self, mensagem: str, status_http: int) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status_http = status_http


class NaoEncontrado(ErroNegocio):
    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem, 404)


class Conflito(ErroNegocio):
    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem, 409)


# Veículos


def cadastrar_veiculo(sessao: Session, dados: VeiculoEntrada) -> Veiculo:
    veiculo = Veiculo(**dados.model_dump())
    sessao.add(veiculo)
    sessao.commit()
    VEICULOS_CADASTRADOS.inc()
    return veiculo


def obter_veiculo(sessao: Session, veiculo_id: str) -> Veiculo:
    veiculo = sessao.get(Veiculo, veiculo_id)
    if not veiculo:
        raise NaoEncontrado("Veículo não encontrado")
    return veiculo


def editar_veiculo(sessao: Session, veiculo_id: str, dados: VeiculoEdicao) -> Veiculo:
    veiculo = obter_veiculo(sessao, veiculo_id)
    if veiculo.status != StatusVeiculo.A_VENDA:
        raise Conflito("Só é possível editar veículos que estão à venda")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(veiculo, campo, valor)
    sessao.commit()
    return veiculo


def listar_veiculos(sessao: Session, status: StatusVeiculo) -> list[Veiculo]:
    consulta = select(Veiculo).where(Veiculo.status == status).order_by(Veiculo.preco.asc(), Veiculo.criado_em)
    return list(sessao.scalars(consulta))


# Vendas


def iniciar_compra(sessao: Session, veiculo_id: str, comprador_id: str) -> Venda:
    veiculo = obter_veiculo(sessao, veiculo_id)
    # UPDATE condicional: em compras simultâneas só uma altera a linha, a outra recebe 409
    reservado = sessao.execute(
        update(Veiculo)
        .where(Veiculo.id == veiculo_id, Veiculo.status == StatusVeiculo.A_VENDA)
        .values(status=StatusVeiculo.RESERVADO, atualizado_em=datetime.now(UTC))
    )
    if reservado.rowcount != 1:
        sessao.rollback()
        raise Conflito("Veículo indisponível para compra")
    venda = Venda(
        veiculo_id=veiculo.id,
        comprador_id=comprador_id,
        preco=veiculo.preco,
        codigo_pagamento=f"PAG-{secrets.token_hex(6)}",
    )
    sessao.add(venda)
    try:
        sessao.commit()
    except IntegrityError as erro:
        sessao.rollback()
        raise Conflito("Veículo indisponível para compra") from erro
    sessao.refresh(venda)
    VENDAS.labels(evento="iniciada").inc()
    return venda


def obter_venda(sessao: Session, venda_id: str) -> Venda:
    venda = sessao.get(Venda, venda_id)
    if not venda:
        raise NaoEncontrado("Venda não encontrada")
    return venda


def listar_vendas(sessao: Session, comprador_id: str | None = None, status: StatusVenda | None = None) -> list[Venda]:
    consulta = select(Venda).order_by(Venda.criada_em.desc())
    if comprador_id:
        consulta = consulta.where(Venda.comprador_id == comprador_id)
    if status:
        consulta = consulta.where(Venda.status == status)
    return list(sessao.scalars(consulta))


def _cancelar(sessao: Session, venda: Venda, motivo: MotivoCancelamento) -> None:
    venda.status = StatusVenda.CANCELADA
    venda.motivo_cancelamento = motivo
    venda.cancelada_em = datetime.now(UTC)
    venda.veiculo.status = StatusVeiculo.A_VENDA
    VENDAS.labels(evento="cancelada").inc()


def cancelar_venda(sessao: Session, venda: Venda, motivo: MotivoCancelamento) -> Venda:
    if venda.status != StatusVenda.AGUARDANDO_PAGAMENTO:
        raise Conflito("Só é possível cancelar vendas aguardando pagamento")
    _cancelar(sessao, venda, motivo)
    sessao.commit()
    return venda


def processar_pagamento(sessao: Session, codigo_pagamento: str, resultado: StatusPagamento) -> Venda:
    # FOR UPDATE para não processar duas notificações da mesma venda ao mesmo tempo
    consulta = select(Venda).where(Venda.codigo_pagamento == codigo_pagamento).with_for_update()
    venda = sessao.scalar(consulta)
    if not venda:
        raise NaoEncontrado("Código de pagamento não encontrado")

    esperado = StatusVenda.EFETIVADA if resultado == StatusPagamento.APROVADO else StatusVenda.CANCELADA
    if venda.status == esperado:
        return venda
    if venda.status != StatusVenda.AGUARDANDO_PAGAMENTO:
        raise Conflito(f"Venda já está {venda.status}")

    if resultado == StatusPagamento.APROVADO:
        venda.status = StatusVenda.EFETIVADA
        venda.efetivada_em = datetime.now(UTC)
        venda.veiculo.status = StatusVeiculo.VENDIDO
        VENDAS.labels(evento="efetivada").inc()
    else:
        _cancelar(sessao, venda, MotivoCancelamento.PAGAMENTO_RECUSADO)
    sessao.commit()
    return venda

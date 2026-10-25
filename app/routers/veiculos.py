from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import services
from app.auth import Gestor
from app.db import obter_sessao
from app.models import StatusVeiculo, Veiculo
from app.schemas import VeiculoEdicao, VeiculoEntrada, VeiculoSaida

router = APIRouter(prefix="/api/v1/veiculos", tags=["Veículos"])
SessaoDep = Annotated[Session, Depends(obter_sessao)]


@router.post("", response_model=VeiculoSaida, status_code=status.HTTP_201_CREATED, summary="Cadastrar veículo")
def cadastrar(dados: VeiculoEntrada, sessao: SessaoDep, _: Gestor) -> Veiculo:
    return services.cadastrar_veiculo(sessao, dados)


@router.get("/a-venda", response_model=list[VeiculoSaida], summary="Veículos à venda (do mais barato ao mais caro)")
def a_venda(sessao: SessaoDep) -> list[Veiculo]:
    return services.listar_veiculos(sessao, StatusVeiculo.A_VENDA)


@router.get("/vendidos", response_model=list[VeiculoSaida], summary="Veículos vendidos (do mais barato ao mais caro)")
def vendidos(sessao: SessaoDep) -> list[Veiculo]:
    return services.listar_veiculos(sessao, StatusVeiculo.VENDIDO)


@router.get("/{veiculo_id}", response_model=VeiculoSaida, summary="Consultar veículo")
def consultar(veiculo_id: str, sessao: SessaoDep) -> Veiculo:
    return services.obter_veiculo(sessao, veiculo_id)


@router.patch("/{veiculo_id}", response_model=VeiculoSaida, summary="Editar veículo")
def editar(veiculo_id: str, dados: VeiculoEdicao, sessao: SessaoDep, _: Gestor) -> Veiculo:
    return services.editar_veiculo(sessao, veiculo_id, dados)

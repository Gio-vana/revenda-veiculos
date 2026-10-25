import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import services
from app.db import obter_sessao
from app.models import Venda
from app.schemas import NotificacaoPagamento, VendaSaida

router = APIRouter(prefix="/api/v1/pagamentos", tags=["Pagamentos"])
SessaoDep = Annotated[Session, Depends(obter_sessao)]


def _validar_segredo(request: Request, x_webhook_secret: Annotated[str | None, Header()] = None) -> None:
    esperado = request.app.state.config.webhook_secret
    if not esperado:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Webhook de pagamento não configurado")
    if not x_webhook_secret or not hmac.compare_digest(x_webhook_secret, esperado):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Segredo do webhook inválido")


@router.post(
    "/webhook",
    response_model=VendaSaida,
    dependencies=[Depends(_validar_segredo)],
    summary="Notificação do gateway de pagamento (efetiva ou cancela a compra)",
    description="Chamado pelo gateway de pagamento (simulado) com o header `X-Webhook-Secret`. "
    "`APROVADO` efetiva a venda e marca o veículo como vendido; `RECUSADO` cancela e devolve o veículo à vitrine.",
)
def webhook(notificacao: NotificacaoPagamento, sessao: SessaoDep) -> Venda:
    return services.processar_pagamento(sessao, notificacao.codigo_pagamento, notificacao.status)

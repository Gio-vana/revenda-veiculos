# ADR-007: Efetivação da compra por webhook do gateway de pagamento

Status: Aceita

## Contexto

O enunciado fala em "compra e efetivação da compra" sem detalhar o pagamento. Uma compra pela internet depende de confirmação de pagamento, que chega de um sistema externo e de forma assíncrona.

## Decisão

- `POST /api/v1/vendas` reserva o veículo, cria a venda `AGUARDANDO_PAGAMENTO` e devolve um `codigo_pagamento` aleatório (`PAG-` + 12 hexadecimais).
- O gateway de pagamento (simulado nesta entrega pelo Swagger, curl ou script de demonstração) chama `POST /api/v1/pagamentos/webhook` com `{codigo_pagamento, status: APROVADO | RECUSADO}` e o header `X-Webhook-Secret`, comparado em tempo constante.
- Com `APROVADO`, a venda fica `EFETIVADA` e o veículo `VENDIDO`. Com `RECUSADO`, a venda fica `CANCELADA` e o veículo volta para `A_VENDA`.
- Idempotente: repetir a mesma notificação devolve 200 sem novo efeito; notificação contraditória (ex.: recusa após aprovação) devolve 409.

## Consequências

- Modelo fiel ao funcionamento real de gateways de pagamento (Stripe, Mercado Pago, PagSeguro usam webhooks).
- Limitação: uma reserva sem pagamento fica pendente até a loja ou o comprador cancelar. Evolução: expiração automática da reserva (ex.: 30 minutos) por job agendado, e assinatura HMAC do corpo do webhook no lugar do segredo compartilhado.

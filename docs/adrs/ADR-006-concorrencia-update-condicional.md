# ADR-006: Concorrência por UPDATE condicional e índice único parcial

**Status:** Aceita

## Contexto

Dois clientes podem tentar comprar o mesmo veículo ao mesmo tempo. Ler o status e depois gravar ("check-then-act") deixaria os dois passarem.

## Decisão

1. A reserva é um único comando atômico:
   `UPDATE veiculos SET status='RESERVADO' WHERE id=:id AND status='A_VENDA'`.
   Se nenhuma linha for alterada, o veículo já não está disponível e a API responde **409**.
2. Como segunda barreira, o índice único parcial `ux_vendas_veiculo_ativa (veiculo_id) WHERE status <> 'CANCELADA'` impede, no banco, duas vendas ativas para o mesmo veículo.
3. O webhook de pagamento trava a venda com `SELECT ... FOR UPDATE`, evitando processar duas notificações simultâneas da mesma venda.

## Alternativas consideradas

- Lock pessimista no veículo (`SELECT ... FOR UPDATE`) na compra: funciona, mas segura a linha por mais tempo.
- Versionamento otimista (coluna `version`): mais código para o mesmo efeito.

## Consequências

- Correto sob concorrência sem locks longos. Coberto pelo teste `test_compras_simultaneas_so_uma_vence` (5 compras simultâneas, exatamente uma vence), executado no CI contra PostgreSQL.

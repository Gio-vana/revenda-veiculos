import threading

import pytest

from tests.conftest import cabecalho, emitir_token


def _comprar(client, headers, veiculo_id):
    return client.post("/api/v1/vendas", json={"veiculo_id": veiculo_id}, headers=headers)


def _pagar(client, webhook, codigo, status="APROVADO"):
    return client.post(
        "/api/v1/pagamentos/webhook", json={"codigo_pagamento": codigo, "status": status}, headers=webhook
    )


def test_fluxo_completo_compra_e_efetivacao(client, cliente, cliente_id, webhook, cadastrar):
    veiculo = cadastrar(preco="80000")

    compra = _comprar(client, cliente, veiculo["id"])

    assert compra.status_code == 201
    venda = compra.json()
    assert venda["status"] == "AGUARDANDO_PAGAMENTO"
    assert venda["comprador_id"] == cliente_id
    assert venda["preco"] == "80000.00"
    assert venda["codigo_pagamento"].startswith("PAG-")
    assert venda["veiculo"]["status"] == "RESERVADO"
    assert client.get("/api/v1/veiculos/a-venda").json() == []

    efetivada = _pagar(client, webhook, venda["codigo_pagamento"])

    assert efetivada.status_code == 200
    assert efetivada.json()["status"] == "EFETIVADA"
    assert efetivada.json()["efetivada_em"] is not None
    vendidos = client.get("/api/v1/veiculos/vendidos").json()
    assert [v["id"] for v in vendidos] == [veiculo["id"]]
    assert vendidos[0]["status"] == "VENDIDO"


def test_listagem_vendidos_ordenada_por_preco(client, cliente, webhook, cadastrar):
    for preco in ("300000", "90000", "150000"):
        veiculo = cadastrar(preco=preco)
        venda = _comprar(client, cliente, veiculo["id"]).json()
        _pagar(client, webhook, venda["codigo_pagamento"])

    precos = [v["preco"] for v in client.get("/api/v1/veiculos/vendidos").json()]

    assert precos == ["90000.00", "150000.00", "300000.00"]


def test_compra_exige_cadastro(client, cadastrar):
    veiculo = cadastrar()

    assert client.post("/api/v1/vendas", json={"veiculo_id": veiculo["id"]}).status_code == 401


def test_gestor_nao_compra(client, gestor, cadastrar):
    veiculo = cadastrar()

    assert _comprar(client, gestor, veiculo["id"]).status_code == 403


def test_veiculo_inexistente_retorna_404(client, cliente):
    assert _comprar(client, cliente, "nao-existe").status_code == 404


def test_segunda_compra_do_mesmo_veiculo_retorna_409(client, cliente, outro_cliente, cadastrar):
    veiculo = cadastrar()
    _comprar(client, cliente, veiculo["id"])

    assert _comprar(client, outro_cliente, veiculo["id"]).status_code == 409


def test_pagamento_recusado_cancela_e_devolve_a_vitrine(client, cliente, webhook, cadastrar):
    veiculo = cadastrar()
    venda = _comprar(client, cliente, veiculo["id"]).json()

    resposta = _pagar(client, webhook, venda["codigo_pagamento"], "RECUSADO")

    assert resposta.json()["status"] == "CANCELADA"
    assert resposta.json()["motivo_cancelamento"] == "PAGAMENTO_RECUSADO"
    assert [v["id"] for v in client.get("/api/v1/veiculos/a-venda").json()] == [veiculo["id"]]


def test_veiculo_cancelado_pode_ser_comprado_de_novo(client, cliente, outro_cliente, webhook, cadastrar):
    veiculo = cadastrar()
    venda = _comprar(client, cliente, veiculo["id"]).json()
    _pagar(client, webhook, venda["codigo_pagamento"], "RECUSADO")

    assert _comprar(client, outro_cliente, veiculo["id"]).status_code == 201


def test_webhook_idempotente(client, cliente, webhook, cadastrar):
    veiculo = cadastrar()
    venda = _comprar(client, cliente, veiculo["id"]).json()
    _pagar(client, webhook, venda["codigo_pagamento"])

    repetida = _pagar(client, webhook, venda["codigo_pagamento"])

    assert repetida.status_code == 200
    assert repetida.json()["status"] == "EFETIVADA"


def test_webhook_conflitante_retorna_409(client, cliente, webhook, cadastrar):
    veiculo = cadastrar()
    venda = _comprar(client, cliente, veiculo["id"]).json()
    _pagar(client, webhook, venda["codigo_pagamento"])

    assert _pagar(client, webhook, venda["codigo_pagamento"], "RECUSADO").status_code == 409


@pytest.mark.parametrize("segredo", [None, "errado"])
def test_webhook_exige_segredo(client, cliente, cadastrar, segredo):
    veiculo = cadastrar()
    venda = _comprar(client, cliente, veiculo["id"]).json()
    headers = {"X-Webhook-Secret": segredo} if segredo else {}

    assert _pagar(client, headers, venda["codigo_pagamento"]).status_code == 401


def test_webhook_codigo_inexistente_retorna_404(client, webhook):
    assert _pagar(client, webhook, "PAG-000000000000").status_code == 404


def test_minhas_compras_mostra_so_as_do_cliente(client, cliente, outro_cliente, cadastrar):
    minha = _comprar(client, cliente, cadastrar()["id"]).json()
    _comprar(client, outro_cliente, cadastrar()["id"])

    resposta = client.get("/api/v1/vendas/minhas", headers=cliente)

    assert [v["id"] for v in resposta.json()] == [minha["id"]]


def test_cliente_nao_ve_venda_de_outro(client, cliente, outro_cliente, cadastrar):
    venda = _comprar(client, cliente, cadastrar()["id"]).json()

    assert client.get(f"/api/v1/vendas/{venda['id']}", headers=cliente).status_code == 200
    assert client.get(f"/api/v1/vendas/{venda['id']}", headers=outro_cliente).status_code == 404


def test_gestor_lista_vendas_com_filtro(client, gestor, cliente, webhook, cadastrar):
    efetivada = _comprar(client, cliente, cadastrar()["id"]).json()
    _pagar(client, webhook, efetivada["codigo_pagamento"])
    _comprar(client, cliente, cadastrar()["id"])

    todas = client.get("/api/v1/vendas", headers=gestor).json()
    filtradas = client.get("/api/v1/vendas", params={"status": "EFETIVADA"}, headers=gestor).json()

    assert len(todas) == 2
    assert [v["id"] for v in filtradas] == [efetivada["id"]]


def test_cliente_nao_lista_todas_as_vendas(client, cliente):
    assert client.get("/api/v1/vendas", headers=cliente).status_code == 403


def test_comprador_desiste_da_compra(client, cliente, cadastrar):
    veiculo = cadastrar()
    venda = _comprar(client, cliente, veiculo["id"]).json()

    resposta = client.post(f"/api/v1/vendas/{venda['id']}/cancelar", headers=cliente)

    assert resposta.json()["motivo_cancelamento"] == "DESISTENCIA_COMPRADOR"
    assert client.get(f"/api/v1/veiculos/{veiculo['id']}").json()["status"] == "A_VENDA"


def test_loja_cancela_venda(client, gestor, cliente, cadastrar):
    venda = _comprar(client, cliente, cadastrar()["id"]).json()

    resposta = client.post(f"/api/v1/vendas/{venda['id']}/cancelar", headers=gestor)

    assert resposta.json()["motivo_cancelamento"] == "CANCELADA_PELA_LOJA"


def test_nao_cancela_venda_efetivada(client, cliente, webhook, cadastrar):
    venda = _comprar(client, cliente, cadastrar()["id"]).json()
    _pagar(client, webhook, venda["codigo_pagamento"])

    assert client.post(f"/api/v1/vendas/{venda['id']}/cancelar", headers=cliente).status_code == 409


def test_compras_simultaneas_so_uma_vence(client, config, cadastrar):
    if config.database_url.startswith("sqlite"):
        pytest.skip("Concorrência real é testada no CI, contra PostgreSQL")
    veiculo = cadastrar()
    resultados: list[int] = []
    barreira = threading.Barrier(5)

    def tentar():
        headers = cabecalho(emitir_token("cliente"))
        barreira.wait()
        resultados.append(_comprar(client, headers, veiculo["id"]).status_code)

    threads = [threading.Thread(target=tentar) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(resultados) == [201, 409, 409, 409, 409]

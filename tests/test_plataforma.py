def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_metricas_de_negocio_expostas(client, cadastrar):
    cadastrar()

    corpo = client.get("/metrics").text

    assert "revenda_veiculos_cadastrados_total" in corpo
    assert "http_requests_total" in corpo


def test_webhook_sem_segredo_configurado_retorna_503(app, client, cliente, cadastrar):
    app.state.config.webhook_secret = None

    resposta = client.post(
        "/api/v1/pagamentos/webhook",
        json={"codigo_pagamento": "PAG-000000000000", "status": "APROVADO"},
        headers={"X-Webhook-Secret": "x"},
    )

    assert resposta.status_code == 503

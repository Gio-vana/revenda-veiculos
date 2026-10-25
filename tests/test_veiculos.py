from datetime import UTC, datetime

import pytest

from tests.conftest import cabecalho, emitir_token


def test_cadastrar_veiculo(client, gestor):
    dados = {"marca": "Honda", "modelo": "Civic", "ano": 2021, "cor": "Preto", "preco": "98500.50"}

    resposta = client.post("/api/v1/veiculos", json=dados, headers=gestor)

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "A_VENDA"
    assert corpo["marca"] == "Honda"
    assert corpo["preco"] == "98500.50"


@pytest.mark.parametrize(
    "invalido",
    [
        {"preco": "0"},
        {"preco": "-10"},
        {"ano": 1800},
        {"ano": datetime.now(UTC).year + 2},
        {"marca": ""},
        {"campo_extra": "x"},
    ],
)
def test_cadastrar_rejeita_dados_invalidos(client, gestor, invalido):
    dados = {"marca": "Honda", "modelo": "Civic", "ano": 2021, "cor": "Preto", "preco": "98500.00", **invalido}

    assert client.post("/api/v1/veiculos", json=dados, headers=gestor).status_code == 422


def test_cliente_nao_cadastra_veiculo(client, cliente):
    dados = {"marca": "Honda", "modelo": "Civic", "ano": 2021, "cor": "Preto", "preco": "98500.00"}

    assert client.post("/api/v1/veiculos", json=dados, headers=cliente).status_code == 403


def test_cadastro_sem_token_retorna_401(client):
    dados = {"marca": "Honda", "modelo": "Civic", "ano": 2021, "cor": "Preto", "preco": "98500.00"}

    assert client.post("/api/v1/veiculos", json=dados).status_code == 401


def test_token_assinado_por_outra_chave_retorna_401(client, chave_estranha):
    falso = cabecalho(emitir_token("gestor", chave=chave_estranha))

    assert client.get("/api/v1/vendas", headers=falso).status_code == 401


def test_token_de_outra_audiencia_retorna_401(client):
    outro = cabecalho(emitir_token("gestor", aud="outra-api"))

    assert client.get("/api/v1/vendas", headers=outro).status_code == 401


def test_editar_veiculo(client, gestor, cadastrar):
    veiculo = cadastrar()

    resposta = client.patch(f"/api/v1/veiculos/{veiculo['id']}", json={"cor": "Azul", "preco": "95000"}, headers=gestor)

    assert resposta.status_code == 200
    assert resposta.json()["cor"] == "Azul"
    assert resposta.json()["preco"] == "95000.00"
    assert resposta.json()["modelo"] == veiculo["modelo"]


def test_editar_sem_campos_retorna_422(client, gestor, cadastrar):
    veiculo = cadastrar()

    assert client.patch(f"/api/v1/veiculos/{veiculo['id']}", json={}, headers=gestor).status_code == 422


def test_editar_com_campo_nulo_retorna_422(client, gestor, cadastrar):
    veiculo = cadastrar()

    assert client.patch(f"/api/v1/veiculos/{veiculo['id']}", json={"preco": None}, headers=gestor).status_code == 422


def test_editar_inexistente_retorna_404(client, gestor):
    assert client.patch("/api/v1/veiculos/nao-existe", json={"cor": "Azul"}, headers=gestor).status_code == 404


def test_editar_veiculo_reservado_retorna_409(client, gestor, cliente, cadastrar):
    veiculo = cadastrar()
    client.post("/api/v1/vendas", json={"veiculo_id": veiculo["id"]}, headers=cliente)

    resposta = client.patch(f"/api/v1/veiculos/{veiculo['id']}", json={"preco": "1"}, headers=gestor)

    assert resposta.status_code == 409


def test_listagem_a_venda_ordenada_por_preco_e_publica(client, cadastrar):
    cadastrar(modelo="Caro", preco="200000")
    cadastrar(modelo="Barato", preco="50000")
    cadastrar(modelo="Medio", preco="120000")

    resposta = client.get("/api/v1/veiculos/a-venda")

    assert resposta.status_code == 200
    assert [v["modelo"] for v in resposta.json()] == ["Barato", "Medio", "Caro"]


def test_consultar_veiculo(client, cadastrar):
    veiculo = cadastrar()

    assert client.get(f"/api/v1/veiculos/{veiculo['id']}").json()["id"] == veiculo["id"]
    assert client.get("/api/v1/veiculos/nao-existe").status_code == 404

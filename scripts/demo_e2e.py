"""Demonstração início-a-fim pelo API Gateway.

Fluxo: cadastro de cliente -> login -> gestor cadastra/edita veículos -> listagem à venda ->
compra -> efetivação pelo webhook de pagamento -> listagem de vendidos.

Uso:
    python scripts/demo_e2e.py --url http://localhost:8080 \
        --gestor-senha <GESTOR_PASSWORD> --webhook-secret <WEBHOOK_SECRET> [--pausa 2]

As senhas também podem vir das variáveis GESTOR_PASSWORD e WEBHOOK_SECRET.
"""

import argparse
import json
import os
import random
import sys
import time
import uuid

import httpx

VERDE, AZUL, AMARELO, VERMELHO, NEGRITO, FIM = "\033[32m", "\033[36m", "\033[33m", "\033[31m", "\033[1m", "\033[0m"


def gerar_cpf() -> str:
    base = [random.randint(0, 9) for _ in range(9)]  # noqa: S311
    for tamanho in (9, 10):
        soma = sum(d * p for d, p in zip(base, range(tamanho + 1, 1, -1), strict=True))
        base.append((soma * 10 % 11) % 10)
    return "".join(map(str, base))


class Demo:
    def __init__(self, url: str, pausa: float) -> None:
        self.http = httpx.Client(base_url=url, timeout=15)
        self.pausa = pausa
        self.passo = 0

    def titulo(self, texto: str) -> None:
        self.passo += 1
        print(f"\n{NEGRITO}{AZUL}== Passo {self.passo}: {texto}{FIM}")
        time.sleep(self.pausa)

    def chamar(self, metodo: str, caminho: str, esperado: int, **kwargs) -> httpx.Response:
        resposta = self.http.request(metodo, caminho, **kwargs)
        cor = VERDE if resposta.status_code == esperado else VERMELHO
        print(f"{AMARELO}{metodo} {caminho}{FIM} -> {cor}{resposta.status_code}{FIM}")
        if resposta.content:
            corpo = resposta.json()
            texto = json.dumps(corpo, ensure_ascii=False, indent=2)
            linhas = texto.splitlines()
            print("\n".join(linhas[:25]) + ("\n  ..." if len(linhas) > 25 else ""))
        if resposta.status_code != esperado:
            sys.exit(f"{VERMELHO}Esperado {esperado}, recebido {resposta.status_code}{FIM}")
        time.sleep(self.pausa)
        return resposta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("GATEWAY_URL", "http://localhost:8080"))
    parser.add_argument("--gestor-email", default=os.environ.get("GESTOR_EMAIL", "gestor@revenda.com.br"))
    parser.add_argument("--gestor-senha", default=os.environ.get("GESTOR_PASSWORD"))
    parser.add_argument("--webhook-secret", default=os.environ.get("WEBHOOK_SECRET"))
    parser.add_argument("--pausa", type=float, default=0, help="segundos entre passos (útil para gravar vídeo)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not args.gestor_senha or not args.webhook_secret:
        parser.error("informe --gestor-senha e --webhook-secret (ou GESTOR_PASSWORD e WEBHOOK_SECRET)")

    demo = Demo(args.url, args.pausa)
    sufixo = uuid.uuid4().hex[:6]
    cliente = {
        "nome": "Maria Compradora",
        "email": f"maria.{sufixo}@exemplo.com",
        "cpf": gerar_cpf(),
        "telefone": "11999998888",
        "senha": "senha-da-maria-123",
    }

    demo.titulo("Visitante tenta comprar sem cadastro (deve ser barrado)")
    demo.chamar("POST", "/api/v1/vendas", 401, json={"veiculo_id": "qualquer"})

    demo.titulo("Cliente se cadastra no serviço de identidade")
    demo.chamar("POST", "/identidade/auth/registro", 201, json=cliente)

    demo.titulo("Cliente faz login e recebe um JWT")
    token_cliente = demo.chamar(
        "POST", "/identidade/auth/login", 200, json={"email": cliente["email"], "senha": cliente["senha"]}
    ).json()["access_token"]
    h_cliente = {"Authorization": f"Bearer {token_cliente}"}

    demo.titulo("Gestor da loja faz login")
    token_gestor = demo.chamar(
        "POST", "/identidade/auth/login", 200, json={"email": args.gestor_email, "senha": args.gestor_senha}
    ).json()["access_token"]
    h_gestor = {"Authorization": f"Bearer {token_gestor}"}

    demo.titulo("Gestor cadastra três veículos")
    veiculos = [
        {"marca": "Toyota", "modelo": "Corolla XEi", "ano": 2022, "cor": "Prata", "preco": "119900.00"},
        {"marca": "Fiat", "modelo": "Argo Drive", "ano": 2021, "cor": "Branco", "preco": "62900.00"},
        {"marca": "Jeep", "modelo": "Compass Longitude", "ano": 2023, "cor": "Preto", "preco": "159900.00"},
    ]
    ids = [demo.chamar("POST", "/api/v1/veiculos", 201, json=v, headers=h_gestor).json()["id"] for v in veiculos]

    demo.titulo("Cliente não pode cadastrar veículo (apenas gestor)")
    demo.chamar("POST", "/api/v1/veiculos", 403, json=veiculos[0], headers=h_cliente)

    demo.titulo("Gestor edita o preço e a cor do Argo")
    demo.chamar(
        "PATCH", f"/api/v1/veiculos/{ids[1]}", 200, json={"preco": "59900.00", "cor": "Vermelho"}, headers=h_gestor
    )

    demo.titulo("Listagem pública de veículos à venda (do mais barato ao mais caro)")
    demo.chamar("GET", "/api/v1/veiculos/a-venda", 200)

    demo.titulo("Cliente compra o Corolla (veículo fica reservado)")
    venda = demo.chamar("POST", "/api/v1/vendas", 201, json={"veiculo_id": ids[0]}, headers=h_cliente).json()

    demo.titulo("Outra compra do mesmo veículo é recusada")
    demo.chamar("POST", "/api/v1/vendas", 409, json={"veiculo_id": ids[0]}, headers=h_cliente)

    demo.titulo("Gateway de pagamento aprova e a compra é efetivada")
    demo.chamar(
        "POST",
        "/api/v1/pagamentos/webhook",
        200,
        json={"codigo_pagamento": venda["codigo_pagamento"], "status": "APROVADO"},
        headers={"X-Webhook-Secret": args.webhook_secret},
    )

    demo.titulo("Cliente compra o Compass, mas o pagamento é recusado")
    venda2 = demo.chamar("POST", "/api/v1/vendas", 201, json={"veiculo_id": ids[2]}, headers=h_cliente).json()
    demo.chamar(
        "POST",
        "/api/v1/pagamentos/webhook",
        200,
        json={"codigo_pagamento": venda2["codigo_pagamento"], "status": "RECUSADO"},
        headers={"X-Webhook-Secret": args.webhook_secret},
    )

    demo.titulo("Minhas compras")
    demo.chamar("GET", "/api/v1/vendas/minhas", 200, headers=h_cliente)

    demo.titulo("Listagem pública de veículos vendidos (do mais barato ao mais caro)")
    demo.chamar("GET", "/api/v1/veiculos/vendidos", 200)

    demo.titulo("Veículos à venda após as compras (Compass voltou à vitrine)")
    demo.chamar("GET", "/api/v1/veiculos/a-venda", 200)

    print(f"\n{NEGRITO}{VERDE}Fluxo início-a-fim concluído com sucesso.{FIM}")


if __name__ == "__main__":
    main()

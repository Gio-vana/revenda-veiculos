from prometheus_client import Counter

VEICULOS_CADASTRADOS = Counter("revenda_veiculos_cadastrados_total", "Veículos cadastrados para venda")
VENDAS = Counter("revenda_vendas_total", "Eventos do ciclo de vida das vendas", ["evento"])

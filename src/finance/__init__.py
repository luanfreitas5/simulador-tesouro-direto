"""Módulo financeiro puro e determinístico (sem I/O, rede ou relógio).

Todas as funções recebem apenas valores e devolvem valores: o mesmo input produz
sempre o mesmo output. Alíquotas e taxas são parâmetros (``TaxParams``) — confira
as regras vigentes antes de usar os resultados.

Módulos
-------
``parameters``
    ``TaxParams``: faixas do IR regressivo, taxa de custódia e convenções de prazo.
calendar
    ``count_business_days``: dias úteis entre duas datas (fins de semana + feriados).
``returns``
    Fatores de crescimento (prefixado, IPCA+, Selic) e fator de inflação.
simulation
    ``simulate_from_growth``: rentabilidade bruta, líquida e real (``SimulationResult``).
"""

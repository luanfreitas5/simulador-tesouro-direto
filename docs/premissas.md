# Premissas e limitações

## Premissas de cálculo

1. Aplicação **mantida até o vencimento** (sem venda antecipada nem marcação a mercado).
2. Títulos *bullet*: Tesouro Prefixado e Tesouro IPCA+ (sem cupons semestrais). A Selic é *benchmark*.
3. Taxa de compra: "Taxa Compra Manha" da última cotação até a data de compra (tolerância de 7 dias).
4. Capitalização em dias úteis (base 252), considerando apenas fins de semana.
5. IPCA acumulado: mensal observado com rateio por dias corridos; depois do último dado, IPCA projetado.
6. Benchmark Selic: Selic diária observada e, depois, Selic projetada.
7. IR regressivo sobre o rendimento positivo: 22,5% (até 180 dias), 20% (181–360), 17,5% (361–720), 15% (acima de 720).
8. Custódia: 0,20% a.a. sobre o saldo médio, rateada por dias corridos.
9. Rentabilidade real pela relação de Fisher.

Todas as alíquotas e taxas ficam em `configs/finance.yaml`.

## Limitações

- Regras e alíquotas mudam: **confira as vigentes**.
- Não modelados: IOF, cobrança semestral real da custódia e isenções, cupons, resgate antecipado.
- IPCA+ simplificado em relação ao VNA oficial.
- Sem calendário de feriados nacionais na contagem de dias úteis.
- Projeções de IPCA e Selic são premissas, não previsões.

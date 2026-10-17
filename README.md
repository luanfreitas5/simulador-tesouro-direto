# 📈 Simulador do Tesouro Direto

[![CI](https://github.com/luanfreitas5/simulador-tesouro-direto/actions/workflows/ci.yml/badge.svg)](https://github.com/luanfreitas5/simulador-tesouro-direto/actions/workflows/ci.yml)
[![Tests](https://github.com/luanfreitas5/simulador-tesouro-direto/actions/workflows/tests.yml/badge.svg)](https://github.com/luanfreitas5/simulador-tesouro-direto/actions/workflows/tests.yml)
[![Docs](https://github.com/luanfreitas5/simulador-tesouro-direto/actions/workflows/docs.yml/badge.svg)](https://luanfreitas5.github.io/simulador-tesouro-direto/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![Polars](https://img.shields.io/badge/dados-Polars-orange)](https://pola.rs)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Curva de juros histórica do Tesouro Direto e simulador de rentabilidade **bruta, líquida e real**
para o mercado brasileiro.

> ⚠️ **Projeto educacional, sem recomendação de investimento.** Alíquotas, taxas e regras mudam.
> **Confira as regras vigentes** (Tesouro Direto, B3 e Receita Federal) antes de usar qualquer
> resultado. Todos os parâmetros ficam em [configs/finance.yaml](configs/finance.yaml) e na barra
> lateral do app.

## 🎯 Problema

Taxas de títulos públicos são divulgadas como "X% ao ano" ou "IPCA + X%", mas o que importa ao
investidor é quanto sobra **depois do imposto, da custódia e da inflação**. Comparar um
Prefixado a um IPCA+ — ou a simplesmente deixar o dinheiro na Selic — exige juntar três coisas
que raramente aparecem juntas: a taxa contratada na data da compra, a inflação do período e as
regras tributárias.

## ❓ Pergunta

> Para uma compra feita em uma data D, de um valor V, em um título com vencimento T, qual é o
> rendimento bruto, líquido e **real** (acima da inflação) ao vencimento — e como isso se
> compara à Selic no mesmo prazo?

Como pergunta complementar: **como a curva de juros (taxa × prazo) do Prefixado e do IPCA+ se
deformou ao longo do tempo?**

## 🗂️ Dados

| Fonte | O que traz | Camada |
|---|---|---|
| [Tesouro Transparente](https://www.tesourotransparente.gov.br) — "Taxas dos Títulos Ofertados pelo Tesouro Direto" | Taxas e PUs de compra/venda por título, vencimento e data (CSV, `;`, decimal com vírgula) | `bronze/tesouro_transparente` |
| [BCB SGS](https://dadosabertos.bcb.gov.br) série **11** | Selic diária (% a.d.) | `bronze/bcb_sgs_11` |
| [BCB SGS](https://dadosabertos.bcb.gov.br) série **433** | IPCA, variação mensal (%) | `bronze/bcb_sgs_433` |

Arquitetura medalhão (os dados **não** são versionados no Git):

```
data/bronze/  snapshots imutáveis, como recebidos + manifest.json (URL, SHA-256, data)
data/silver/  limpos, tipados, deduplicados e validados (Pandera): tesouro_prices, selic_daily, ipca_monthly
data/gold/    yield_curve.parquet — curva de juros pronta para o app
```

A ingestão é **idempotente** e usa **cache local**: dentro do TTL (24 h, configurável) nenhuma
requisição é feita; se o conteúdo baixado tiver o mesmo SHA-256, nenhum snapshot novo é criado; se
a rede falhar e houver snapshot, ele é reutilizado com um aviso. A URL do CSV é configurável em
[configs/config.yaml](configs/config.yaml) caso o portal mude o endereço do recurso.

## 🚀 Como reproduzir

Requisitos: Python 3.10+ e [uv](https://docs.astral.sh/uv/).

```bash
make install-app   # uv sync --dev --extra app (gere o uv.lock com `uv lock` na primeira vez)
make pipeline      # ingestão (bronze) -> silver -> gold -> gráficos HTML em reports/figures/
make app           # abre o simulador Streamlit
make test          # pytest com cobertura mínima de 80%
make quality       # ruff, basedpyright, bandit, pip-audit, vulture, xenon, interrogate, refurb
```

Etapas isoladas: `make ingest`, `make build`, `make plots` (ou
`uv run python src/main.py {ingest|build|plots|all} [--force]`). `--force` ignora o cache.

## 🧮 Módulo financeiro

[src/finance/](src/finance/) é **puro e determinístico** (sem I/O, rede ou relógio) e recebe
alíquotas e taxas por parâmetro (`TaxParams`):

- `calculate_compound_factor`, `calculate_ipca_plus_factor`, `calculate_selic_factor`,
  `calculate_inflation_factor` — fatores de crescimento;
- `calculate_ir_rate` — IR regressivo por faixas de prazo;
- `calculate_custody_cost` — taxa de custódia;
- `simulate_from_growth` — rentabilidade bruta, líquida e real (`SimulationResult`).

Exemplo (R$ 1.000 com +10% bruto em 365 dias; IR 17,5% e custódia de 0,20% a.a.):

```python
from finance.simulation import simulate_from_growth

r = simulate_from_growth(1000.0, 1.10, 365, inflation_factor=1.05)
r.ir_amount  # 17.50
r.custody_cost  # 2.10
r.net_final  # 1080.40
r.real_return  # ≈ 0.0290 (≈ 2,90% acima da inflação de 5%)
```

Cobertura de testes: fronteiras das faixas de IR (180/181, 360/361, 720/721), prejuízo e
rendimento nulo (sem IR), custódia zero, prazos e valores inválidos, mês parcial de IPCA, projeção
após o último dado observado, fins de semana e feriados, além de propriedades (`hypothesis`):
líquido nunca excede o bruto, líquido é monotônico no rendimento e o IR nunca sobe com o prazo.

## 📊 Resultados

O projeto entrega:

- **Curva de juros navegável por data** (Prefixado e IPCA+): gráfico Plotly com slider em
  `reports/figures/yield_curve_*.html` e no app Streamlit (aba *Curva de juros*).
- **Simulador** (aba *Simulador*): título, data de compra, valor e vencimento → valor bruto e
  líquido final, rentabilidade líquida e real ao ano, cascata *investido → bruto → IR → custódia →
  líquido* e comparação com a Selic no mesmo valor e prazo.

### Execução do pipeline (`make pipeline`, 17/10/2026)

| Camada | Artefato | Registros | Período |
|---|---|---:|---|
| Silver | `tesouro_prices.parquet` | 177.434 | 31/12/2004 a 15/10/2026 |
| Silver | `selic_daily.parquet` | 6.229 | 02/01/2002 a 16/10/2026 |
| Silver | `ipca_monthly.parquet` | 297 | 01/2002 a 09/2026 |
| Gold | `yield_curve.parquet` | 47.157 (28.215 Prefixado; 18.942 IPCA+) | 31/12/2004 a 15/10/2026 |

Todos os contratos de dados (`pandera`) passaram e os dois gráficos HTML foram gerados em
`reports/figures/`. A execução completa, com os dados já em cache, levou cerca de 5 s.

### Curva de juros na última data (15/10/2026)

| Título | Vencimento | Prazo (anos) | Taxa de compra (% a.a.) |
|---|---|---:|---:|
| Prefixado | 01/01/2027 | 0,2 | 13,37 |
| Prefixado | 01/01/2028 | 1,2 | 12,77 |
| Prefixado | 01/01/2029 | 2,2 | 12,64 |
| Prefixado | 01/01/2031 | 4,2 | 12,76 |
| Prefixado | 01/01/2032 | 5,2 | 12,87 |
| IPCA+ | 15/05/2029 | 2,6 | 6,77 (real) |
| IPCA+ | 15/08/2032 | 5,8 | 6,80 (real) |
| IPCA+ | 15/05/2035 | 8,6 | 6,84 (real) |
| IPCA+ | 15/08/2040 | 13,8 | 6,73 (real) |
| IPCA+ | 15/05/2045 | 18,6 | 6,73 (real) |
| IPCA+ | 15/08/2050 | 23,8 | 6,74 (real) |

A curva Prefixada está **invertida** no curto prazo (13,37% em 0,2 ano contra 12,64% em 2,2 anos),
enquanto a curva real do IPCA+ é praticamente plana (6,7% a 6,8%).

### Simulações de exemplo

R$ 10.000 comprados em 15/10/2026 e mantidos até o vencimento, com IR regressivo e custódia de
0,20% a.a. Para o trecho sem dado observado, assume-se IPCA de 4,5% a.a. e Selic de 12% a.a.
(premissas do usuário, **não** previsões). O benchmark aplica a Selic ao mesmo valor e prazo.

| Título | Líquido final | Líquido a.a. | Real a.a. | Benchmark Selic (líquido a.a.) |
|---|---:|---:|---:|---:|
| Prefixado 2029 (12,64%) | R$ 12.611,67 | 11,04% | 6,26% | 10,47% |
| IPCA+ 2035 (IPCA + 6,84%) | R$ 23.511,07 | 10,47% | 5,71% | 10,97% |

O Prefixado 2029 supera a Selic projetada de 12% a.a. porque trava 12,64%. Já o IPCA+ 2035 fica
abaixo dela, pois a Selic assumida (12%) implica juro real alto frente ao IPCA de 4,5%. A
conclusão depende inteiramente dessas premissas e muda se elas mudarem.

> Os números dependem da data de execução (o Tesouro atualiza os dados diariamente), então esta
> seção é um retrato de 17/10/2026. Para reproduzir, rode `make pipeline`.

## 📐 Premissas de cálculo

1. **Mantido até o vencimento.** Não há venda antecipada nem marcação a mercado.
2. **Títulos "bullet".** Apenas Tesouro Prefixado e Tesouro IPCA+ (sem cupons semestrais). A Selic
   entra como *benchmark*, não como título simulado.
3. **Taxa de compra.** Usa a "Taxa Compra Manha" da última cotação disponível até a data de
   compra (tolerância de 7 dias, para fins de semana e feriados).
4. **Capitalização em dias úteis (base 252).** Prefixado: `valor × (1 + taxa)^(du/252)`. IPCA+:
   `valor × (1 + taxa real)^(du/252) × IPCA acumulado`. Dias úteis excluem apenas fins de semana
   (o calendário de feriados ANBIMA não está embutido; `count_business_days` aceita feriados).
5. **IPCA acumulado.** IPCA mensal observado (SGS 433), com rateio proporcional aos dias corridos
   do mês cobertos pelo período; o trecho posterior ao último mês publicado usa o **IPCA anual
   projetado** (parâmetro; padrão ilustrativo de 4% a.a.).
6. **Benchmark Selic.** Selic diária observada (SGS 11) e, depois do último dado, **Selic anual
   projetada** (parâmetro; padrão ilustrativo de 10% a.a.), sobre o mesmo valor e prazo, com as
   mesmas regras de IR e custódia.
7. **IR regressivo** sobre o rendimento positivo, pelo prazo em dias corridos: até 180 dias 22,5%;
   181–360 dias 20%; 361–720 dias 17,5%; acima de 720 dias 15%. Sem IR (nem crédito) se houver
   prejuízo.
8. **Custódia.** 0,20% a.a. sobre o saldo médio (média entre investido e bruto final), rateada por
   dias corridos e deduzida do valor final.
9. **Rentabilidade real.** `(1 + retorno líquido) / (1 + inflação do período) − 1` (Fisher), e
   anualizada por dias corridos / 365.

## ⚠️ Limitações

- **Regras e alíquotas mudam**; os valores acima são parâmetros configuráveis, não verdade
  imutável. Confira a regra vigente.
- **Não modelados:** IOF (resgates com menos de 30 dias), cobrança semestral real da taxa de
  custódia sobre o saldo e eventuais isenções, cupons semestrais, resgate antecipado e
  marcação a mercado.
- **IPCA+ simplificado.** O Tesouro corrige o VNA com a variação do IPCA com defasagem e
  projeção pro rata; aqui o rateio é feito por dias corridos dentro de cada mês. Diferenças
  pequenas são esperadas.
- **Calendário.** Sem feriados nacionais, a contagem de dias úteis é ligeiramente maior que a real.
- **Projeções são premissas**, não previsões; resultados com muito período futuro dependem
  fortemente do IPCA e da Selic assumidos.
- **Dados:** o CSV traz as taxas "da manhã"; a execução efetiva da compra pode ocorrer em outro
  preço. A URL do recurso no Tesouro Transparente pode mudar.
- **Sem recomendação de investimento.** Projeto de portfólio com fins educacionais.

## 🧱 Estrutura

```
configs/        YAML validados com Pydantic (config, paths, finance, logging)
src/            config, constants, data, preprocessing, schemas, features, finance,
                pipelines, visualization, utils, exceptions, main.py
app/            streamlit_app.py
tests/          unitários, propriedades (hypothesis) e integração (sem rede)
notebooks/      01_eda_curva_de_juros.ipynb
data/           bronze | silver | gold (fora do Git)
docs/           MkDocs Material + mkdocstrings
```

Decisões de engenharia: Polars (sem pandas), contratos de dados Pandera em cada fronteira de
camada, download injetável (testes sem rede), logs em pt-BR com Rich e arquivo diário, hooks de
pre-commit rápidos e checagens pesadas no CI.

## 📄 Licença

[MIT](LICENSE)

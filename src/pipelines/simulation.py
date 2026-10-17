"""Simulação de uma compra do Tesouro Direto mantida até o vencimento.

Une a curva histórica (taxa de compra na data) às séries IPCA/Selic e ao módulo
financeiro puro (``finance``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import polars as pl

from config.settings import FinanceSettings
from constants.bonds import BOND_PREFIXED, SIMULATED_BONDS
from exceptions import DataNotFoundError, InvalidInputError
from finance.calendar import count_business_days
from finance.parameters import TaxParams
from finance.returns import (
    calculate_compound_factor,
    calculate_inflation_factor,
    calculate_ipca_plus_factor,
    calculate_selic_factor,
)
from finance.simulation import SimulationResult, simulate_from_growth

MAX_QUOTE_GAP_DAYS = 7  # tolerância entre a data de compra e a última cotação disponível


@dataclass(frozen=True)
class SimulationRequest:
    """Entradas do simulador.

    Parameters
    ----------
    bond_type : str
        ``"Tesouro Prefixado"`` ou ``"Tesouro IPCA+"``.
    purchase_date : date
        Data da compra (usa a última cotação disponível até esta data).
    amount : float
        Valor investido (reais).
    maturity_date : date
        Vencimento do título.
    projected_ipca_annual : float
        IPCA anual assumido (fração) para o trecho sem dado observado.
    projected_selic_annual : float
        Selic anual assumida (fração) para o trecho sem dado observado.
    """

    bond_type: str
    purchase_date: date
    amount: float
    maturity_date: date
    projected_ipca_annual: float
    projected_selic_annual: float


@dataclass(frozen=True)
class SimulationOutcome:
    """Resultado do título e do benchmark Selic para o mesmo prazo e valor."""

    request: SimulationRequest
    quote_date: date
    annual_rate: float
    business_days: int
    result: SimulationResult
    benchmark: SimulationResult


def build_tax_params(finance: FinanceSettings) -> TaxParams:
    """Converte a configuração validada em ``TaxParams`` do módulo financeiro.

    Parameters
    ----------
    finance : FinanceSettings
        Configuração financeira (YAML).

    Returns
    -------
    TaxParams
        Parâmetros imutáveis para os cálculos.
    """
    return TaxParams(
        ir_brackets=tuple((bracket.max_days, bracket.rate) for bracket in finance.ir_brackets),
        ir_floor_rate=finance.ir_floor_rate,
        custody_fee_annual=finance.custody_fee_annual,
        business_days_per_year=finance.business_days_per_year,
    )


def find_quote_date(
    curve: pl.DataFrame,
    bond_type: str,
    purchase_date: date,
    max_gap_days: int = MAX_QUOTE_GAP_DAYS,
) -> date:
    """Encontra a última data de cotação do título até ``purchase_date``.

    Parameters
    ----------
    curve : pl.DataFrame
        Curva de juros (camada gold).
    bond_type : str
        Título desejado.
    purchase_date : date
        Data de compra.
    max_gap_days : int, optional
        Distância máxima aceita entre a compra e a cotação, by default 7.

    Returns
    -------
    date
        Data da cotação utilizada.

    Raises
    ------
    DataNotFoundError
        Se não houver cotação anterior ou ela estiver além da tolerância.
    """
    dates = curve.filter(
        (pl.col("bond_type") == bond_type) & (pl.col("reference_date") <= purchase_date)
    )["reference_date"]
    latest = dates.max() if dates.len() else None
    if not isinstance(latest, date) or (purchase_date - latest).days > max_gap_days:
        raise DataNotFoundError(
            f"Sem cotação de '{bond_type}' até {purchase_date} (tolerância de {max_gap_days} dias)."
        )
    return latest


def list_available_maturities(
    curve: pl.DataFrame, bond_type: str, purchase_date: date
) -> list[date]:
    """Lista os vencimentos ofertados na cotação vigente em ``purchase_date``.

    Parameters
    ----------
    curve : pl.DataFrame
        Curva de juros (camada gold).
    bond_type : str
        Título desejado.
    purchase_date : date
        Data de compra.

    Returns
    -------
    list[date]
        Vencimentos em ordem crescente.

    Raises
    ------
    DataNotFoundError
        Se não houver cotação utilizável.
    """
    quote_date = find_quote_date(curve, bond_type, purchase_date)
    rows = curve.filter(
        (pl.col("bond_type") == bond_type) & (pl.col("reference_date") == quote_date)
    )
    return rows["maturity_date"].sort().to_list()


def lookup_purchase_rate(
    curve: pl.DataFrame, bond_type: str, maturity_date: date, quote_date: date
) -> float:
    """Obtém a taxa de compra (fração a.a.) de um título numa data de cotação.

    Parameters
    ----------
    curve : pl.DataFrame
        Curva de juros (camada gold; taxas em % a.a.).
    bond_type : str
        Título.
    maturity_date : date
        Vencimento.
    quote_date : date
        Data da cotação.

    Returns
    -------
    float
        Taxa anual em fração (0.105 = 10,5% a.a.).

    Raises
    ------
    DataNotFoundError
        Se o vencimento não foi ofertado naquela data.
    """
    rows = curve.filter(
        (pl.col("bond_type") == bond_type)
        & (pl.col("maturity_date") == maturity_date)
        & (pl.col("reference_date") == quote_date)
    )
    if rows.height == 0:
        raise DataNotFoundError(
            f"'{bond_type}' com vencimento em {maturity_date} não ofertado em {quote_date}."
        )
    return float(rows["buy_rate"][0]) / 100.0


def _to_pairs(series: pl.DataFrame) -> list[tuple[date, float]]:
    return list(zip(series["reference_date"].to_list(), series["value"].to_list(), strict=True))


def run_simulation(
    request: SimulationRequest,
    curve: pl.DataFrame,
    ipca: pl.DataFrame,
    selic: pl.DataFrame,
    params: TaxParams,
) -> SimulationOutcome:
    """Simula a compra de um título mantido até o vencimento e o benchmark Selic.

    O Prefixado capitaliza a taxa contratada em dias úteis (252). O IPCA+ capitaliza
    a taxa real e multiplica pelo IPCA acumulado (observado + projeção). O benchmark
    aplica a Selic observada e a projeção sobre o mesmo valor e prazo, com as mesmas
    regras de IR e custódia.

    Parameters
    ----------
    request : SimulationRequest
        Entradas do usuário e premissas de projeção.
    curve : pl.DataFrame
        Curva de juros (gold).
    ipca : pl.DataFrame
        IPCA mensal (silver: ``reference_date``, ``value`` em %).
    selic : pl.DataFrame
        Selic diária (silver: ``reference_date``, ``value`` em % a.d.).
    params : TaxParams
        Alíquotas e taxas.

    Returns
    -------
    SimulationOutcome
        Resultado do título e do benchmark.

    Raises
    ------
    InvalidInputError
        Se o título não for suportado ou datas/valor forem inválidos.
    DataNotFoundError
        Se não houver cotação para o título/vencimento.

    Examples
    --------
    >>> outcome = run_simulation(request, curve, ipca, selic, params)  # doctest: +SKIP
    """
    if request.bond_type not in SIMULATED_BONDS:
        raise InvalidInputError(f"Título não suportado: {request.bond_type}")
    if request.maturity_date <= request.purchase_date:
        raise InvalidInputError("O vencimento deve ser posterior à data de compra.")

    quote_date = find_quote_date(curve, request.bond_type, request.purchase_date)
    annual_rate = lookup_purchase_rate(curve, request.bond_type, request.maturity_date, quote_date)
    start, end = request.purchase_date, request.maturity_date
    business_days = count_business_days(start, end)
    inflation = calculate_inflation_factor(
        _to_pairs(ipca), start, end, request.projected_ipca_annual, params.calendar_days_per_year
    )

    bdpy = params.business_days_per_year
    if request.bond_type == BOND_PREFIXED:
        growth = calculate_compound_factor(annual_rate, business_days, bdpy)
    else:  # Tesouro IPCA+
        growth = calculate_ipca_plus_factor(annual_rate, business_days, inflation, bdpy)

    selic_growth = calculate_selic_factor(
        _to_pairs(selic), start, end, request.projected_selic_annual, business_days_per_year=bdpy
    )
    holding_days = (end - start).days
    return SimulationOutcome(
        request=request,
        quote_date=quote_date,
        annual_rate=annual_rate,
        business_days=business_days,
        result=simulate_from_growth(request.amount, growth, holding_days, inflation, params),
        benchmark=simulate_from_growth(
            request.amount, selic_growth, holding_days, inflation, params
        ),
    )

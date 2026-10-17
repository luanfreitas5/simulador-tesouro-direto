"""Rentabilidade bruta, líquida (IR regressivo + custódia) e real de uma aplicação."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from exceptions import InvalidInputError
from finance.parameters import DEFAULT_TAX_PARAMS, TaxParams


@dataclass(frozen=True)
class SimulationResult:
    """Resultado de uma simulação de aplicação mantida até o vencimento.

    Valores monetários em reais; retornos em fração (0.10 = 10%); anualizados por
    dias corridos (``holding_days / calendar_days_per_year``).
    """

    invested: float
    holding_days: int
    growth_factor: float
    gross_final: float
    gross_profit: float
    gross_return: float
    gross_annualized: float
    ir_rate: float
    ir_amount: float
    custody_cost: float
    net_final: float
    net_profit: float
    net_return: float
    net_annualized: float
    inflation_factor: float
    real_return: float
    real_annualized: float

    def to_dict(self) -> dict[str, float]:
        """Converte o resultado em dicionário.

        Returns
        -------
        dict[str, float]
            Mapa ``campo -> valor``.
        """
        return {key: float(value) for key, value in asdict(self).items()}


def calculate_ir_rate(holding_days: int, params: TaxParams = DEFAULT_TAX_PARAMS) -> float:
    """Retorna a alíquota do IR regressivo para o prazo da aplicação.

    Parameters
    ----------
    holding_days : int
        Prazo em dias corridos (não negativo).
    params : TaxParams, optional
        Faixas e alíquota final, by default ``DEFAULT_TAX_PARAMS``.

    Returns
    -------
    float
        Alíquota sobre o rendimento (fração).

    Raises
    ------
    InvalidInputError
        Se ``holding_days`` for negativo.

    Examples
    --------
    >>> calculate_ir_rate(180), calculate_ir_rate(181), calculate_ir_rate(721)
    (0.225, 0.2, 0.15)
    """
    if holding_days < 0:
        raise InvalidInputError("O prazo da aplicação não pode ser negativo.")
    for max_days, rate in params.ir_brackets:
        if holding_days <= max_days:
            return rate
    return params.ir_floor_rate


def calculate_custody_cost(
    invested: float,
    gross_final: float,
    holding_days: int,
    params: TaxParams = DEFAULT_TAX_PARAMS,
) -> float:
    """Estima a taxa de custódia sobre o saldo médio da aplicação.

    Aproxima o saldo pela média entre o valor investido e o bruto final e ratea a
    taxa anual por dias corridos: ``taxa * (dias / 365) * saldo_médio``.

    Parameters
    ----------
    invested : float
        Valor investido.
    gross_final : float
        Valor bruto no vencimento.
    holding_days : int
        Prazo em dias corridos.
    params : TaxParams, optional
        Taxa de custódia e convenção de dias, by default ``DEFAULT_TAX_PARAMS``.

    Returns
    -------
    float
        Custo total de custódia no período (reais).

    Examples
    --------
    >>> round(calculate_custody_cost(1000.0, 1100.0, 365), 2)
    2.1
    """
    average_balance = (invested + gross_final) / 2.0
    years = holding_days / params.calendar_days_per_year
    return params.custody_fee_annual * years * average_balance


def _annualize(total_return: float, years: float) -> float:
    base = 1.0 + total_return
    if base <= 0:
        return -1.0
    return base ** (1.0 / years) - 1.0


def _validate_simulation_inputs(
    invested: float, growth_factor: float, holding_days: int, inflation_factor: float
) -> None:
    if invested <= 0:
        raise InvalidInputError("O valor investido deve ser positivo.")
    if growth_factor <= 0:
        raise InvalidInputError("O fator de crescimento deve ser positivo.")
    if holding_days <= 0:
        raise InvalidInputError("O prazo da aplicação deve ser de pelo menos 1 dia.")
    if inflation_factor <= 0:
        raise InvalidInputError("O fator de inflação deve ser positivo.")


def simulate_from_growth(
    invested: float,
    growth_factor: float,
    holding_days: int,
    inflation_factor: float = 1.0,
    params: TaxParams = DEFAULT_TAX_PARAMS,
) -> SimulationResult:
    """Calcula rentabilidade bruta, líquida e real a partir do fator de crescimento bruto.

    Fluxo: ``bruto = investido * fator``; IR incide só sobre o rendimento positivo
    (``alíquota(prazo)``); a custódia é deduzida do valor final; o retorno real
    deflaciona o retorno líquido pela inflação (Fisher).

    Parameters
    ----------
    invested : float
        Valor investido (> 0).
    growth_factor : float
        Fator bruto de crescimento até o vencimento (> 0; 1.10 = +10%).
    holding_days : int
        Prazo em dias corridos (>= 1).
    inflation_factor : float, optional
        Fator acumulado de inflação no período (> 0), by default 1.0.
    params : TaxParams, optional
        Alíquotas e taxas, by default ``DEFAULT_TAX_PARAMS``.

    Returns
    -------
    SimulationResult
        Resultado detalhado da simulação.

    Raises
    ------
    InvalidInputError
        Se algum argumento for inválido.

    Examples
    --------
    >>> result = simulate_from_growth(1000.0, 1.10, 365)
    >>> round(result.net_final, 2)
    1080.4
    """
    _validate_simulation_inputs(invested, growth_factor, holding_days, inflation_factor)
    gross_final = invested * growth_factor
    gross_profit = gross_final - invested
    ir_rate = calculate_ir_rate(holding_days, params)
    ir_amount = max(gross_profit, 0.0) * ir_rate
    custody_cost = calculate_custody_cost(invested, gross_final, holding_days, params)
    net_final = gross_final - ir_amount - custody_cost

    years = holding_days / params.calendar_days_per_year
    gross_return = growth_factor - 1.0
    net_return = net_final / invested - 1.0
    real_return = (1.0 + net_return) / inflation_factor - 1.0
    return SimulationResult(
        invested=invested,
        holding_days=holding_days,
        growth_factor=growth_factor,
        gross_final=gross_final,
        gross_profit=gross_profit,
        gross_return=gross_return,
        gross_annualized=_annualize(gross_return, years),
        ir_rate=ir_rate,
        ir_amount=ir_amount,
        custody_cost=custody_cost,
        net_final=net_final,
        net_profit=net_final - invested,
        net_return=net_return,
        net_annualized=_annualize(net_return, years),
        inflation_factor=inflation_factor,
        real_return=real_return,
        real_annualized=_annualize(real_return, years),
    )

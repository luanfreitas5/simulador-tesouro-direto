"""Testes unitários do módulo financeiro: IR regressivo, custódia, bruto/líquido/real."""

from __future__ import annotations

import pytest

from exceptions import InvalidInputError
from finance.parameters import TaxParams
from finance.simulation import (
    calculate_custody_cost,
    calculate_ir_rate,
    simulate_from_growth,
)

pytestmark = pytest.mark.smoke

NO_FEES = TaxParams(ir_brackets=(), ir_floor_rate=0.0, custody_fee_annual=0.0)


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (0, 0.225),
        (180, 0.225),
        (181, 0.20),
        (360, 0.20),
        (361, 0.175),
        (720, 0.175),
        (721, 0.15),
        (5000, 0.15),
    ],
)
def test_ir_rate_brackets_and_boundaries(days: int, expected: float) -> None:
    """As fronteiras das faixas são inclusivas no limite superior."""
    assert calculate_ir_rate(days) == expected


def test_ir_rate_rejects_negative_days() -> None:
    """Prazo negativo é inválido."""
    with pytest.raises(InvalidInputError):
        calculate_ir_rate(-1)


def test_ir_rate_uses_custom_params() -> None:
    """Alíquotas e faixas são parâmetros, não constantes."""
    params = TaxParams(ir_brackets=((100, 0.5),), ir_floor_rate=0.1)
    assert calculate_ir_rate(100, params) == 0.5
    assert calculate_ir_rate(101, params) == 0.1


def test_custody_cost_uses_average_balance() -> None:
    """Custódia = taxa * anos * saldo médio."""
    assert calculate_custody_cost(1000.0, 1100.0, 365) == pytest.approx(2.1)


def test_known_case_gross_net_and_real() -> None:
    """1000 a +10% em 365 dias: IR 17,5% e custódia de 0,20% a.a."""
    result = simulate_from_growth(1000.0, 1.10, 365, inflation_factor=1.05)
    assert result.gross_final == pytest.approx(1100.0)
    assert result.ir_rate == 0.175
    assert result.ir_amount == pytest.approx(17.5)
    assert result.custody_cost == pytest.approx(2.1)
    assert result.net_final == pytest.approx(1080.4)
    assert result.net_return == pytest.approx(0.0804)
    assert result.net_annualized == pytest.approx(0.0804)
    assert result.real_return == pytest.approx(1.0804 / 1.05 - 1)


def test_zero_fees_and_zero_ir_keep_gross() -> None:
    """Sem IR nem custódia, líquido = bruto."""
    result = simulate_from_growth(1000.0, 1.10, 400, params=NO_FEES)
    assert result.net_final == pytest.approx(result.gross_final)


def test_loss_pays_no_income_tax() -> None:
    """Rendimento negativo não gera IR (nem crédito)."""
    result = simulate_from_growth(1000.0, 0.90, 365)
    assert result.ir_amount == 0.0
    assert result.gross_profit == pytest.approx(-100.0)
    assert result.net_final == pytest.approx(900.0 - 1.9)


def test_zero_profit_pays_no_income_tax() -> None:
    """Rendimento nulo não gera IR."""
    assert simulate_from_growth(1000.0, 1.0, 365).ir_amount == 0.0


def test_gross_annualized_over_two_years() -> None:
    """21% em 730 dias (2 anos de 365) equivale a 10% a.a."""
    result = simulate_from_growth(1000.0, 1.21, 730, params=NO_FEES)
    assert result.gross_annualized == pytest.approx(0.10)


def test_total_loss_annualizes_to_minus_one() -> None:
    """Retorno de -100% ou pior fica limitado a -100% a.a."""
    result = simulate_from_growth(1000.0, 1e-9, 365, params=NO_FEES)
    assert result.net_annualized == pytest.approx(-1.0, abs=1e-6)


@pytest.mark.parametrize(
    ("invested", "growth", "days", "inflation"),
    [
        (0, 1.1, 365, 1.0),
        (-5, 1.1, 365, 1.0),
        (1000, 0, 365, 1.0),
        (1000, 1.1, 0, 1.0),
        (1000, 1.1, 365, 0),
    ],
)
def test_invalid_inputs_raise(invested: float, growth: float, days: int, inflation: float) -> None:
    """Entradas inválidas levantam InvalidInputError (também é ValueError)."""
    with pytest.raises(InvalidInputError):
        simulate_from_growth(invested, growth, days, inflation)
    with pytest.raises(ValueError):
        simulate_from_growth(invested, growth, days, inflation)


def test_result_to_dict_has_all_fields() -> None:
    """to_dict expõe todos os campos numéricos."""
    data = simulate_from_growth(1000.0, 1.1, 365).to_dict()
    assert {"gross_final", "net_final", "real_annualized", "holding_days"} <= set(data)
    assert all(isinstance(v, float) for v in data.values())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ir_brackets": ((360, 0.2), (180, 0.3))},
        {"ir_brackets": ((0, 0.2),)},
        {"ir_brackets": ((180, 1.5),)},
        {"ir_floor_rate": -0.1},
        {"custody_fee_annual": 1.0},
        {"business_days_per_year": 0},
    ],
)
def test_tax_params_validation(kwargs: dict) -> None:
    """Parâmetros inconsistentes falham na construção."""
    with pytest.raises(InvalidInputError):
        TaxParams(**kwargs)

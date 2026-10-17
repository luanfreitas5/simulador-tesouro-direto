"""Testes unitários dos fatores de crescimento, inflação e dias úteis."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from exceptions import InvalidInputError
from finance.calendar import count_business_days
from finance.returns import (
    calculate_compound_factor,
    calculate_inflation_factor,
    calculate_ipca_plus_factor,
    calculate_selic_factor,
)

pytestmark = pytest.mark.smoke


def test_compound_factor_full_and_half_year() -> None:
    """252 du = 1 ano; 126 du = raiz do fator anual."""
    assert calculate_compound_factor(0.10, 252) == pytest.approx(1.10)
    assert calculate_compound_factor(0.10, 126) == pytest.approx(1.10**0.5)
    assert calculate_compound_factor(0.10, 0) == 1.0


@pytest.mark.parametrize(
    ("rate", "days", "bdpy"), [(-1.0, 10, 252), (-2.0, 10, 252), (0.1, -1, 252), (0.1, 10, 0)]
)
def test_compound_factor_invalid(rate: float, days: int, bdpy: int) -> None:
    """Taxa <= -100%, dias negativos ou convenção inválida levantam erro."""
    with pytest.raises(InvalidInputError):
        calculate_compound_factor(rate, days, bdpy)


def test_ipca_plus_factor_combines_real_rate_and_inflation() -> None:
    """IPCA+ = (1 + juro real) ** (du/252) * inflação acumulada."""
    assert calculate_ipca_plus_factor(0.05, 252, 1.04) == pytest.approx(1.092)
    with pytest.raises(InvalidInputError):
        calculate_ipca_plus_factor(0.05, 252, 0.0)


def test_inflation_full_months() -> None:
    """Meses inteiros entram com o IPCA cheio."""
    ipca = [(date(2024, 1, 1), 1.0), (date(2024, 2, 1), 2.0)]
    factor = calculate_inflation_factor(ipca, date(2024, 1, 1), date(2024, 3, 1), 0.04)
    assert factor == pytest.approx(1.01 * 1.02)


def test_inflation_pro_rata_partial_month() -> None:
    """Mês parcial entra proporcional aos dias cobertos."""
    ipca = [(date(2024, 1, 1), 1.0)]
    factor = calculate_inflation_factor(ipca, date(2024, 1, 16), date(2024, 2, 1), 0.04)
    assert factor == pytest.approx(1.01 ** (16 / 31))


def test_inflation_projects_after_last_observed_month() -> None:
    """Após o último mês observado, aplica-se a inflação projetada."""
    ipca = [(date(2024, 1, 1), 1.0)]
    end = date(2024, 2, 1) + timedelta(days=365)
    factor = calculate_inflation_factor(ipca, date(2024, 1, 1), end, 0.05)
    assert factor == pytest.approx(1.01 * 1.05)


def test_inflation_without_series_is_pure_projection() -> None:
    """Sem série observada, todo o período é projetado."""
    start = date(2024, 1, 1)
    factor = calculate_inflation_factor([], start, start + timedelta(days=365), 0.04)
    assert factor == pytest.approx(1.04)


def test_inflation_ignores_months_outside_period_and_zero_length() -> None:
    """Meses fora do período não contribuem; período vazio dá fator 1."""
    ipca = [(date(2023, 6, 1), 5.0)]
    day = date(2024, 1, 1)
    assert calculate_inflation_factor(ipca, day, day, 0.04) == 1.0


def test_inflation_invalid_inputs() -> None:
    """Datas invertidas ou projeção <= -100% levantam erro."""
    with pytest.raises(InvalidInputError):
        calculate_inflation_factor([], date(2024, 2, 1), date(2024, 1, 1), 0.04)
    with pytest.raises(InvalidInputError):
        calculate_inflation_factor([], date(2024, 1, 1), date(2024, 2, 1), -1.0)


def test_selic_realized_only() -> None:
    """Dias observados são compostos; sem projeção quando o fim é coberto."""
    daily = [(date(2024, 1, 8), 0.04), (date(2024, 1, 9), 0.04), (date(2024, 1, 10), 0.04)]
    factor = calculate_selic_factor(daily, date(2024, 1, 8), date(2024, 1, 11), 0.10)
    assert factor == pytest.approx(1.0004**3)


def test_selic_projects_remaining_business_days() -> None:
    """Depois do último dado, projeta a taxa anual em dias úteis."""
    daily = [(date(2024, 1, 8), 0.04), (date(2024, 1, 9), 0.04), (date(2024, 1, 10), 0.04)]
    factor = calculate_selic_factor(daily, date(2024, 1, 8), date(2024, 1, 12), 0.10)
    assert factor == pytest.approx(1.0004**3 * 1.10 ** (1 / 252))


def test_selic_without_series_and_dates_beyond_end() -> None:
    """Sem série: projeção pura. Dados após o fim são ignorados."""
    start, end = date(2024, 1, 8), date(2024, 1, 15)
    assert calculate_selic_factor([], start, end, 0.10) == pytest.approx(1.10 ** (5 / 252))
    future = [(date(2024, 2, 1), 0.04)]
    assert calculate_selic_factor(future, start, end, 0.10) == 1.0


def test_selic_invalid_dates() -> None:
    """Datas invertidas levantam erro."""
    with pytest.raises(InvalidInputError):
        calculate_selic_factor([], date(2024, 2, 1), date(2024, 1, 1), 0.1)


def test_business_days_weekdays_weekend_and_holidays() -> None:
    """Conta dias úteis em [início, fim), excluindo fins de semana e feriados."""
    assert count_business_days(date(2024, 1, 1), date(2024, 1, 8)) == 5
    assert count_business_days(date(2024, 1, 6), date(2024, 1, 8)) == 0
    assert count_business_days(date(2024, 1, 1), date(2024, 1, 1)) == 0
    assert count_business_days(date(2024, 1, 1), date(2024, 1, 8), [date(2024, 1, 3)]) == 4
    with pytest.raises(InvalidInputError):
        count_business_days(date(2024, 1, 8), date(2024, 1, 1))

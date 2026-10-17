"""Testes da simulação de compra: cotação, vencimentos, prefixado, IPCA+ e benchmark Selic."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import polars as pl
import pytest

from config.settings import FinanceSettings
from exceptions import DataNotFoundError, InvalidInputError
from finance.calendar import count_business_days
from finance.parameters import TaxParams
from pipelines.simulation import (
    SimulationRequest,
    build_tax_params,
    find_quote_date,
    list_available_maturities,
    lookup_purchase_rate,
    run_simulation,
)

Frames = tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]

PREFIXED = "Tesouro Prefixado"
IPCA_PLUS = "Tesouro IPCA+"


def _request(bond: str, maturity: date, purchase: date = date(2024, 1, 2)) -> SimulationRequest:
    return SimulationRequest(bond, purchase, 10_000.0, maturity, 0.04, 0.10)


def test_build_tax_params_matches_defaults() -> None:
    """A configuração padrão gera os mesmos TaxParams padrão do módulo financeiro."""
    assert build_tax_params(FinanceSettings()) == TaxParams()


def test_find_quote_date_uses_last_available_within_tolerance(processed: Frames) -> None:
    """Sábado usa a cotação de sexta/quarta anterior; muito distante ou antes dos dados falha."""
    curve = processed[0]
    assert find_quote_date(curve, PREFIXED, date(2024, 1, 6)) == date(2024, 1, 3)
    with pytest.raises(DataNotFoundError):
        find_quote_date(curve, PREFIXED, date(2024, 2, 1))
    with pytest.raises(DataNotFoundError):
        find_quote_date(curve, PREFIXED, date(2023, 12, 1))


def test_list_available_maturities_follows_quote_date(processed: Frames) -> None:
    """Lista apenas os vencimentos ofertados na cotação vigente."""
    curve = processed[0]
    assert list_available_maturities(curve, PREFIXED, date(2024, 1, 2)) == [
        date(2027, 1, 1),
        date(2029, 1, 1),
    ]
    assert list_available_maturities(curve, PREFIXED, date(2024, 1, 3)) == [date(2027, 1, 1)]


def test_lookup_purchase_rate_returns_fraction(processed: Frames) -> None:
    """A taxa em % a.a. vira fração; vencimento inexistente falha."""
    curve = processed[0]
    assert lookup_purchase_rate(curve, PREFIXED, date(2027, 1, 1), date(2024, 1, 2)) == 0.105
    with pytest.raises(DataNotFoundError):
        lookup_purchase_rate(curve, PREFIXED, date(2030, 1, 1), date(2024, 1, 2))


def test_prefixed_simulation_matches_closed_form(processed: Frames) -> None:
    """Bruto = valor * (1 + taxa) ** (du / 252); líquido e real consistentes."""
    curve, ipca, selic = processed
    maturity = date(2027, 1, 1)
    outcome = run_simulation(_request(PREFIXED, maturity), curve, ipca, selic, TaxParams())

    business_days = count_business_days(date(2024, 1, 2), maturity)
    assert outcome.business_days == business_days
    assert outcome.annual_rate == 0.105
    assert outcome.result.gross_final == pytest.approx(10_000 * 1.105 ** (business_days / 252))
    assert outcome.result.holding_days == (maturity - date(2024, 1, 2)).days
    assert outcome.result.net_final < outcome.result.gross_final
    assert outcome.result.real_return < outcome.result.net_return
    assert outcome.benchmark.invested == 10_000.0


def test_ipca_plus_simulation_includes_inflation(processed: Frames) -> None:
    """Bruto = valor * (1 + juro real) ** (du / 252) * inflação acumulada."""
    curve, ipca, selic = processed
    maturity = date(2035, 5, 15)
    outcome = run_simulation(_request(IPCA_PLUS, maturity), curve, ipca, selic, TaxParams())

    result = outcome.result
    expected = 10_000 * 1.06 ** (outcome.business_days / 252) * result.inflation_factor
    assert result.gross_final == pytest.approx(expected)
    assert result.inflation_factor > 1.0


def test_higher_projected_inflation_raises_ipca_plus_gross(processed: Frames) -> None:
    """Direcional: mais inflação projetada aumenta o bruto do IPCA+, mas não o do Prefixado."""
    curve, ipca, selic = processed
    low = _request(IPCA_PLUS, date(2035, 5, 15))
    high = replace(low, projected_ipca_annual=0.08)
    assert (
        run_simulation(high, curve, ipca, selic, TaxParams()).result.gross_final
        > run_simulation(low, curve, ipca, selic, TaxParams()).result.gross_final
    )


def test_invalid_requests_raise(processed: Frames) -> None:
    """Título não suportado, vencimento anterior à compra ou não ofertado."""
    curve, ipca, selic = processed
    with pytest.raises(InvalidInputError):
        run_simulation(_request("Tesouro Selic", date(2027, 3, 1)), curve, ipca, selic, TaxParams())
    with pytest.raises(InvalidInputError):
        run_simulation(_request(PREFIXED, date(2024, 1, 2)), curve, ipca, selic, TaxParams())
    with pytest.raises(DataNotFoundError):
        run_simulation(_request(PREFIXED, date(2030, 1, 1)), curve, ipca, selic, TaxParams())

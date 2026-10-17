"""Testes baseados em propriedades (hypothesis) do módulo financeiro."""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from finance.returns import calculate_compound_factor, calculate_inflation_factor
from finance.simulation import calculate_ir_rate, simulate_from_growth

TOLERANCE = 1e-6

amounts = st.floats(min_value=30.0, max_value=1_000_000.0)
growths = st.floats(min_value=0.5, max_value=3.0)
days = st.integers(min_value=1, max_value=7_300)


@settings(deadline=None)
@given(invested=amounts, growth=growths, holding=days)
def test_net_never_exceeds_gross(invested: float, growth: float, holding: int) -> None:
    """Invariante: IR e custódia só reduzem o valor final."""
    result = simulate_from_growth(invested, growth, holding)
    assert result.net_final <= result.gross_final + TOLERANCE
    assert result.ir_amount >= 0
    assert result.custody_cost >= 0


@settings(deadline=None)
@given(invested=amounts, g1=growths, g2=growths, holding=days)
def test_net_is_monotonic_in_growth(invested: float, g1: float, g2: float, holding: int) -> None:
    """Invariante: mais rendimento bruto nunca reduz o líquido."""
    low, high = sorted((g1, g2))
    net_low = simulate_from_growth(invested, low, holding).net_final
    net_high = simulate_from_growth(invested, high, holding).net_final
    assert net_low <= net_high + TOLERANCE


@given(d1=st.integers(min_value=0, max_value=10_000), d2=st.integers(min_value=0, max_value=10_000))
def test_ir_rate_is_non_increasing_with_time(d1: int, d2: int) -> None:
    """Invariante: o IR regressivo nunca aumenta com o prazo."""
    short, long = sorted((d1, d2))
    assert calculate_ir_rate(short) >= calculate_ir_rate(long)


@given(rate=st.floats(min_value=0.0, max_value=1.0), business_days=st.integers(0, 5_000))
def test_compound_factor_at_least_one_for_non_negative_rates(
    rate: float, business_days: int
) -> None:
    """Invariante: taxa não negativa nunca encolhe o capital."""
    assert calculate_compound_factor(rate, business_days) >= 1.0


@given(
    monthly=st.lists(st.floats(min_value=0.0, max_value=5.0), max_size=12),
    span=st.integers(min_value=0, max_value=1_500),
)
def test_inflation_factor_at_least_one_for_non_negative_inflation(
    monthly: list[float], span: int
) -> None:
    """Invariante: IPCA e projeção não negativos nunca deflacionam o período."""
    ipca = [(date(2024, 1 + i, 1), pct) for i, pct in enumerate(monthly)]
    start = date(2024, 1, 1)
    assert calculate_inflation_factor(ipca, start, start + timedelta(days=span), 0.04) >= 1.0

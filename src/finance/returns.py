"""Fatores de crescimento dos títulos e fator de inflação do período."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, timedelta

from exceptions import InvalidInputError
from finance.calendar import count_business_days

DEFAULT_BUSINESS_DAYS_PER_YEAR = 252
DEFAULT_CALENDAR_DAYS_PER_YEAR = 365


def calculate_compound_factor(
    annual_rate: float,
    business_days: int,
    business_days_per_year: int = DEFAULT_BUSINESS_DAYS_PER_YEAR,
) -> float:
    """Capitaliza uma taxa anual em dias úteis: ``(1 + taxa) ** (du / 252)``.

    Parameters
    ----------
    annual_rate : float
        Taxa anual em fração (0.10 = 10% a.a.); deve ser maior que -1.
    business_days : int
        Dias úteis do período (não negativo).
    business_days_per_year : int, optional
        Convenção de dias úteis por ano, by default 252.

    Returns
    -------
    float
        Fator de crescimento do período.

    Raises
    ------
    InvalidInputError
        Se a taxa for ``<= -1``, os dias forem negativos ou a convenção não for positiva.

    Examples
    --------
    >>> calculate_compound_factor(0.10, 252)
    1.1
    """
    if annual_rate <= -1:
        raise InvalidInputError(f"A taxa anual deve ser maior que -100%; recebido: {annual_rate}")
    if business_days < 0:
        raise InvalidInputError("Os dias úteis não podem ser negativos.")
    if business_days_per_year <= 0:
        raise InvalidInputError("Os dias úteis por ano devem ser positivos.")
    return (1.0 + annual_rate) ** (business_days / business_days_per_year)


def calculate_ipca_plus_factor(
    real_rate: float,
    business_days: int,
    inflation_factor: float,
    business_days_per_year: int = DEFAULT_BUSINESS_DAYS_PER_YEAR,
) -> float:
    """Fator bruto do IPCA+: juro real capitalizado vezes a inflação do período.

    Parameters
    ----------
    real_rate : float
        Taxa real anual contratada (fração).
    business_days : int
        Dias úteis do período.
    inflation_factor : float
        Fator acumulado do IPCA no período (``> 0``).
    business_days_per_year : int, optional
        Convenção de dias úteis por ano, by default 252.

    Returns
    -------
    float
        Fator de crescimento bruto.

    Raises
    ------
    InvalidInputError
        Se ``inflation_factor <= 0`` ou os demais argumentos forem inválidos.

    Examples
    --------
    >>> round(calculate_ipca_plus_factor(0.05, 252, 1.04), 4)
    1.092
    """
    if inflation_factor <= 0:
        raise InvalidInputError("O fator de inflação deve ser positivo.")
    compound = calculate_compound_factor(real_rate, business_days, business_days_per_year)
    return compound * inflation_factor


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _next_month_start(value: date) -> date:
    first = _month_start(value)
    return date(first.year + (first.month == 12), first.month % 12 + 1, 1)


def calculate_inflation_factor(
    monthly_ipca: Iterable[tuple[date, float]],
    start: date,
    end: date,
    projected_annual_rate: float,
    calendar_days_per_year: int = DEFAULT_CALENDAR_DAYS_PER_YEAR,
) -> float:
    """Acumula o IPCA em ``[start, end)``, com rateio proporcional e projeção.

    Cada mês observado entra com ``(1 + ipca) ** (dias_sobrepostos / dias_do_mês)``.
    O trecho posterior ao último mês observado usa ``projected_annual_rate``
    capitalizada por dias corridos.

    Parameters
    ----------
    monthly_ipca : Iterable[tuple[date, float]]
        Pares ``(data_do_mês, variação_em_%)``; o dia é ignorado (mês de referência).
    start : date
        Início do período (inclusivo).
    end : date
        Fim do período (exclusivo).
    projected_annual_rate : float
        IPCA anual assumido (fração) para o período sem dado observado.
    calendar_days_per_year : int, optional
        Dias corridos por ano na projeção, by default 365.

    Returns
    -------
    float
        Fator acumulado de inflação (1.0 = sem inflação).

    Raises
    ------
    InvalidInputError
        Se ``end < start`` ou a projeção for ``<= -100%``.

    Examples
    --------
    >>> ipca = [(date(2024, 1, 1), 1.0)]
    >>> round(calculate_inflation_factor(ipca, date(2024, 1, 1), date(2024, 2, 1), 0.04), 4)
    1.01
    """
    if end < start:
        raise InvalidInputError(f"A data final ({end}) é anterior à inicial ({start}).")
    if projected_annual_rate <= -1:
        raise InvalidInputError("A inflação projetada deve ser maior que -100%.")

    factor = 1.0
    observed_until = start
    for reference, pct in sorted(monthly_ipca):
        month_start = _month_start(reference)
        month_end = _next_month_start(reference)
        overlap_days = (min(end, month_end) - max(start, month_start)).days
        if overlap_days > 0:
            month_days = (month_end - month_start).days
            factor *= (1.0 + pct / 100.0) ** (overlap_days / month_days)
        observed_until = max(observed_until, month_end)

    projected_days = max((end - observed_until).days, 0)
    return factor * (1.0 + projected_annual_rate) ** (projected_days / calendar_days_per_year)


def calculate_selic_factor(
    daily_selic: Sequence[tuple[date, float]],
    start: date,
    end: date,
    projected_annual_rate: float,
    holidays: Iterable[date] = (),
    business_days_per_year: int = DEFAULT_BUSINESS_DAYS_PER_YEAR,
) -> float:
    """Acumula a Selic diária em ``[start, end)`` e projeta o trecho restante.

    Parameters
    ----------
    daily_selic : Sequence[tuple[date, float]]
        Pares ``(data, taxa_diária_em_%)`` (série SGS 11, dias úteis).
    start : date
        Início do período (inclusivo).
    end : date
        Fim do período (exclusivo).
    projected_annual_rate : float
        Selic anual assumida (fração) após o último dado observado.
    holidays : Iterable[date], optional
        Feriados para a contagem de dias úteis da projeção, by default vazio.
    business_days_per_year : int, optional
        Convenção de dias úteis por ano, by default 252.

    Returns
    -------
    float
        Fator acumulado da Selic no período.

    Raises
    ------
    InvalidInputError
        Se ``end < start`` ou a projeção for inválida.

    Examples
    --------
    >>> selic = [(date(2024, 1, 8), 0.04)]
    >>> round(calculate_selic_factor(selic, date(2024, 1, 8), date(2024, 1, 9), 0.10), 6)
    1.0004
    """
    if end < start:
        raise InvalidInputError(f"A data final ({end}) é anterior à inicial ({start}).")

    factor = 1.0
    last_observed = start - timedelta(days=1)
    for reference, pct in daily_selic:
        if start <= reference < end:
            factor *= 1.0 + pct / 100.0
        last_observed = max(last_observed, min(reference, end - timedelta(days=1)))

    projection_start = last_observed + timedelta(days=1)
    if projection_start >= end:
        return factor
    projected_days = count_business_days(projection_start, end, holidays)
    return factor * calculate_compound_factor(
        projected_annual_rate, projected_days, business_days_per_year
    )

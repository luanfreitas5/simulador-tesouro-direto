"""Contagem de dias úteis."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

import numpy as np

from exceptions import InvalidInputError


def count_business_days(start: date, end: date, holidays: Iterable[date] = ()) -> int:
    """Conta os dias úteis no intervalo ``[start, end)``.

    Considera apenas fins de semana e os feriados informados. O calendário oficial
    de feriados (ANBIMA) não está embutido: passe-o em ``holidays`` se necessário.

    Parameters
    ----------
    start : date
        Data inicial (inclusiva).
    end : date
        Data final (exclusiva).
    holidays : Iterable[date], optional
        Feriados a desconsiderar, by default vazio.

    Returns
    -------
    int
        Quantidade de dias úteis.

    Raises
    ------
    InvalidInputError
        Se ``end`` for anterior a ``start``.

    Examples
    --------
    >>> count_business_days(date(2024, 1, 1), date(2024, 1, 8))
    5
    """
    if end < start:
        raise InvalidInputError(f"A data final ({end}) é anterior à inicial ({start}).")
    holiday_array = np.array([np.datetime64(h, "D") for h in holidays], dtype="datetime64[D]")
    first = np.datetime64(start, "D")
    last = np.datetime64(end, "D")
    return int(np.busday_count(first, last, holidays=holiday_array))

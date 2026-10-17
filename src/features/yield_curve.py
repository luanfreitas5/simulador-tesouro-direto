"""Curva de juros histórica por data de referência (camada gold)."""

from __future__ import annotations

from collections.abc import Sequence

import polars as pl

from constants.bonds import DAYS_PER_YEAR_CURVE, GOLD_CURVE_COLUMNS, SIMULATED_BONDS


def build_yield_curve(
    silver: pl.DataFrame, bond_types: Sequence[str] = SIMULATED_BONDS
) -> pl.DataFrame:
    """Constrói a curva de juros: taxa de compra por vencimento em cada data.

    Mantém apenas os títulos solicitados com taxa de compra disponível e
    vencimento posterior à data de referência, e adiciona ``years_to_maturity``
    (dias corridos / 365,25) para o eixo X da curva.

    Parameters
    ----------
    silver : pl.DataFrame
        Preços e taxas limpos (saída de ``clean_tesouro``).
    bond_types : Sequence[str], optional
        Títulos incluídos, by default Prefixado e IPCA+.

    Returns
    -------
    pl.DataFrame
        Colunas ``reference_date``, ``bond_type``, ``maturity_date``,
        ``years_to_maturity``, ``buy_rate`` e ``sell_rate`` (taxas em % a.a.),
        ordenadas por título, data e vencimento.

    Examples
    --------
    >>> curve = build_yield_curve(silver)  # doctest: +SKIP
    """
    return (
        silver.lazy()
        .filter(pl.col("bond_type").is_in(list(bond_types)) & pl.col("buy_rate").is_not_null())
        .with_columns(
            (
                (pl.col("maturity_date") - pl.col("reference_date")).dt.total_days()
                / DAYS_PER_YEAR_CURVE
            ).alias("years_to_maturity")
        )
        .filter(pl.col("years_to_maturity") > 0)
        .select(list(GOLD_CURVE_COLUMNS))
        .sort(["bond_type", "reference_date", "maturity_date"])
        .collect()
    )

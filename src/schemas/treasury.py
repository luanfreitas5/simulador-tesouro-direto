"""Contratos de dados dos preços e taxas do Tesouro Direto (silver e gold)."""

from __future__ import annotations

import logging

import pandera.polars as pa
import polars as pl
from pandera.errors import SchemaError, SchemaErrors

from constants.bonds import SIMULATED_BONDS
from exceptions import DataValidationError

logger = logging.getLogger(__name__)

# Taxas em % a.a.; IPCA+ já teve taxas reais ligeiramente negativas.
_RATE_RANGE = pa.Check.in_range(-10.0, 60.0)
_NON_NEGATIVE = pa.Check.ge(0.0)

TESOURO_SILVER_KEY = ["bond_type", "maturity_date", "reference_date"]

TESOURO_SILVER_SCHEMA = pa.DataFrameSchema(
    {
        "bond_type": pa.Column(pl.String, nullable=False),
        "maturity_date": pa.Column(pl.Date, nullable=False),
        "reference_date": pa.Column(pl.Date, nullable=False),
        "buy_rate": pa.Column(pl.Float64, _RATE_RANGE, nullable=True),
        "sell_rate": pa.Column(pl.Float64, _RATE_RANGE, nullable=True),
        "buy_price": pa.Column(pl.Float64, _NON_NEGATIVE, nullable=True),
        "sell_price": pa.Column(pl.Float64, _NON_NEGATIVE, nullable=True),
        "base_price": pa.Column(pl.Float64, _NON_NEGATIVE, nullable=True),
    },
    strict=True,
)

YIELD_CURVE_GOLD_SCHEMA = pa.DataFrameSchema(
    {
        "reference_date": pa.Column(pl.Date, nullable=False),
        "bond_type": pa.Column(pl.String, pa.Check.isin(list(SIMULATED_BONDS)), nullable=False),
        "maturity_date": pa.Column(pl.Date, nullable=False),
        "years_to_maturity": pa.Column(pl.Float64, pa.Check.gt(0.0), nullable=False),
        "buy_rate": pa.Column(pl.Float64, _RATE_RANGE, nullable=False),
        "sell_rate": pa.Column(pl.Float64, _RATE_RANGE, nullable=True),
    },
    strict=True,
)


def _validate(
    df: pl.DataFrame, schema: pa.DataFrameSchema, key: list[str], name: str
) -> pl.DataFrame:
    """Valida ``df`` contra ``schema`` e garante unicidade da chave ``key``."""
    try:
        validated = schema.validate(df)
    except (SchemaError, SchemaErrors) as exc:
        logger.exception("Contrato de dados violado em %s", name)
        raise DataValidationError(f"Contrato de dados violado em {name}: {exc}") from exc
    if df.select(key).is_duplicated().any():
        raise DataValidationError(f"Chave duplicada {key} em {name}.")
    return validated


def validate_tesouro_silver(df: pl.DataFrame) -> pl.DataFrame:
    """Valida a camada silver de preços e taxas do Tesouro.

    Parameters
    ----------
    df : pl.DataFrame
        Dados limpos (saída de ``clean_tesouro``).

    Returns
    -------
    pl.DataFrame
        O mesmo DataFrame, se válido.

    Raises
    ------
    DataValidationError
        Se tipos, intervalos, colunas ou a unicidade da chave forem violados.
    """
    return _validate(df, TESOURO_SILVER_SCHEMA, TESOURO_SILVER_KEY, "silver/tesouro")


def validate_yield_curve_gold(df: pl.DataFrame) -> pl.DataFrame:
    """Valida a curva de juros da camada gold.

    Parameters
    ----------
    df : pl.DataFrame
        Curva de juros (saída de ``build_yield_curve``).

    Returns
    -------
    pl.DataFrame
        O mesmo DataFrame, se válido.

    Raises
    ------
    DataValidationError
        Se o contrato for violado.
    """
    return _validate(df, YIELD_CURVE_GOLD_SCHEMA, TESOURO_SILVER_KEY, "gold/yield_curve")

"""Contrato de dados das séries macroeconômicas (Selic e IPCA) da camada silver."""

from __future__ import annotations

import logging

import pandera.polars as pa
import polars as pl
from pandera.errors import SchemaError, SchemaErrors

from exceptions import DataValidationError

logger = logging.getLogger(__name__)

MACRO_SILVER_SCHEMA = pa.DataFrameSchema(
    {
        "reference_date": pa.Column(pl.Date, nullable=False),
        "value": pa.Column(pl.Float64, pa.Check.in_range(-5.0, 50.0), nullable=False),
    },
    strict=True,
)


def validate_macro_silver(df: pl.DataFrame, name: str) -> pl.DataFrame:
    """Valida uma série macro (``reference_date``, ``value`` em %) da camada silver.

    Parameters
    ----------
    df : pl.DataFrame
        Série limpa (saída de ``clean_sgs``).
    name : str
        Nome da série (usado nas mensagens de erro).

    Returns
    -------
    pl.DataFrame
        O mesmo DataFrame, se válido.

    Raises
    ------
    DataValidationError
        Se o contrato for violado ou houver datas duplicadas.
    """
    try:
        validated = MACRO_SILVER_SCHEMA.validate(df)
    except (SchemaError, SchemaErrors) as exc:
        logger.exception("Contrato de dados violado em silver/%s", name)
        raise DataValidationError(f"Contrato de dados violado em silver/{name}: {exc}") from exc
    if df["reference_date"].is_duplicated().any():
        raise DataValidationError(f"Datas duplicadas em silver/{name}.")
    return validated

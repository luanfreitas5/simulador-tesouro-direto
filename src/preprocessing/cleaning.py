"""Limpeza dos dados brutos: tipagem, renomeação, deduplicação e ordenação."""

from __future__ import annotations

import polars as pl

from constants.bonds import RAW_TESOURO_COLUMNS, SGS_DATE_FORMAT, TESOURO_DATE_FORMAT
from exceptions import DataValidationError
from schemas.treasury import TESOURO_SILVER_KEY


def _parse_decimal(column: str) -> pl.Expr:
    """Converte texto com vírgula decimal em ``Float64`` (inválido/vazio vira nulo)."""
    return (
        pl.col(column)
        .str.strip_chars()
        .str.replace_all(",", ".", literal=True)
        .cast(pl.Float64, strict=False)
    )


def _normalize_columns(raw: pl.DataFrame) -> pl.DataFrame:
    """Remove BOM e espaços dos nomes de colunas."""
    return raw.rename({col: col.lstrip("﻿").strip() for col in raw.columns})


def clean_tesouro(raw: pl.DataFrame) -> pl.DataFrame:
    """Converte o CSV bruto do Tesouro Transparente na camada silver.

    Renomeia as colunas para inglês, converte datas (``dd/mm/aaaa``) e números
    (vírgula decimal), remove duplicatas pela chave
    ``(bond_type, maturity_date, reference_date)`` e ordena. Taxas em % a.a.

    Parameters
    ----------
    raw : pl.DataFrame
        DataFrame bruto (todas as colunas como texto).

    Returns
    -------
    pl.DataFrame
        Dados tipados e deduplicados.

    Raises
    ------
    DataValidationError
        Se alguma coluna esperada estiver ausente no CSV.

    Examples
    --------
    >>> clean_tesouro(read_tesouro_csv(path))  # doctest: +SKIP
    """
    raw = _normalize_columns(raw)
    missing = sorted(set(RAW_TESOURO_COLUMNS) - set(raw.columns))
    if missing:
        raise DataValidationError(f"Colunas ausentes no CSV do Tesouro: {missing}")

    return (
        raw.select(
            pl.col("Tipo Titulo").str.strip_chars().alias("bond_type"),
            pl.col("Data Vencimento")
            .str.strip_chars()
            .str.to_date(TESOURO_DATE_FORMAT)
            .alias("maturity_date"),
            pl.col("Data Base")
            .str.strip_chars()
            .str.to_date(TESOURO_DATE_FORMAT)
            .alias("reference_date"),
            _parse_decimal("Taxa Compra Manha").alias("buy_rate"),
            _parse_decimal("Taxa Venda Manha").alias("sell_rate"),
            _parse_decimal("PU Compra Manha").alias("buy_price"),
            _parse_decimal("PU Venda Manha").alias("sell_price"),
            _parse_decimal("PU Base Manha").alias("base_price"),
        )
        .unique(subset=TESOURO_SILVER_KEY, keep="last", maintain_order=True)
        .sort(["bond_type", "maturity_date", "reference_date"])
    )


def clean_sgs(raw: pl.DataFrame) -> pl.DataFrame:
    """Converte uma série bruta do SGS (``data``/``valor``) na camada silver.

    Parameters
    ----------
    raw : pl.DataFrame
        DataFrame bruto com as colunas ``data`` e ``valor`` (texto).

    Returns
    -------
    pl.DataFrame
        Colunas ``reference_date`` (Date) e ``value`` (Float64, em %), sem nulos,
        sem datas duplicadas e ordenadas.

    Raises
    ------
    DataValidationError
        Se as colunas ``data`` ou ``valor`` estiverem ausentes.

    Examples
    --------
    >>> clean_sgs(read_sgs_json(path))  # doctest: +SKIP
    """
    if not {"data", "valor"}.issubset(raw.columns):
        raise DataValidationError("A série do SGS deve conter as colunas 'data' e 'valor'.")
    return (
        raw.select(
            pl.col("data").str.strip_chars().str.to_date(SGS_DATE_FORMAT).alias("reference_date"),
            pl.col("valor").str.strip_chars().cast(pl.Float64, strict=False).alias("value"),
        )
        .drop_nulls()
        .unique(subset=["reference_date"], keep="last", maintain_order=True)
        .sort("reference_date")
    )

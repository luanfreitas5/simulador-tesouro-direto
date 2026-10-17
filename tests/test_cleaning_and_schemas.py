"""Testes da limpeza (bronze -> silver), dos contratos de dados e da curva (gold)."""

from __future__ import annotations

import io
from datetime import date

import polars as pl
import pytest

from exceptions import DataValidationError
from features.yield_curve import build_yield_curve
from preprocessing.cleaning import clean_sgs, clean_tesouro
from schemas.macro import validate_macro_silver
from schemas.treasury import validate_tesouro_silver, validate_yield_curve_gold


@pytest.fixture
def raw_tesouro(tesouro_csv: str) -> pl.DataFrame:
    """CSV sintético do Tesouro lido como texto."""
    return pl.read_csv(io.BytesIO(tesouro_csv.encode()), separator=";", infer_schema=False)


@pytest.fixture
def silver(raw_tesouro: pl.DataFrame) -> pl.DataFrame:
    """Silver sintética obtida do CSV de teste."""
    return clean_tesouro(raw_tesouro)


def test_clean_tesouro_types_dedup_and_nulls(silver: pl.DataFrame) -> None:
    """Datas e números são tipados, a duplicata some e campos vazios viram nulo."""
    assert silver.schema["reference_date"] == pl.Date
    assert silver.schema["buy_rate"] == pl.Float64
    assert silver.height == 8  # 9 linhas - 1 duplicata
    first = silver.filter(
        (pl.col("bond_type") == "Tesouro Prefixado")
        & (pl.col("maturity_date") == date(2027, 1, 1))
        & (pl.col("reference_date") == date(2024, 1, 2))
    )
    assert first["buy_rate"].to_list() == [10.5]
    empty_rate = silver.filter(pl.col("maturity_date") == date(2025, 7, 1))
    assert empty_rate["buy_rate"].to_list() == [None]


def test_clean_tesouro_missing_column_raises() -> None:
    """CSV sem colunas esperadas falha com mensagem clara."""
    with pytest.raises(DataValidationError, match="Colunas ausentes"):
        clean_tesouro(pl.DataFrame({"Tipo Titulo": ["x"]}))


def test_clean_tesouro_strips_bom_from_header(raw_tesouro: pl.DataFrame) -> None:
    """BOM e espaços nos nomes de colunas são removidos."""
    renamed = raw_tesouro.rename({"Tipo Titulo": "﻿Tipo Titulo"})
    assert clean_tesouro(renamed).height == 8


def test_validate_tesouro_silver_accepts_clean_data(silver: pl.DataFrame) -> None:
    """Dados limpos respeitam o contrato."""
    assert validate_tesouro_silver(silver).height == silver.height


def test_validate_tesouro_silver_rejects_violations(silver: pl.DataFrame) -> None:
    """Preço negativo, coluna extra e chave duplicada violam o contrato."""
    with pytest.raises(DataValidationError):
        validate_tesouro_silver(silver.with_columns(pl.lit(-1.0).alias("buy_price")))
    with pytest.raises(DataValidationError):
        validate_tesouro_silver(silver.with_columns(pl.lit(1).alias("extra")))
    with pytest.raises(DataValidationError, match="duplicada"):
        validate_tesouro_silver(pl.concat([silver, silver.head(1)]))


def test_build_yield_curve_filters_and_computes_years(silver: pl.DataFrame) -> None:
    """Só Prefixado/IPCA+ com taxa e vencimento futuro; adiciona prazo em anos."""
    curve = build_yield_curve(silver)
    assert set(curve["bond_type"].unique()) == {"Tesouro Prefixado", "Tesouro IPCA+"}
    assert curve.height == 5  # sem Selic, sem taxa nula, sem vencimento passado
    assert (curve["years_to_maturity"] > 0).all()
    row = curve.filter(
        (pl.col("maturity_date") == date(2027, 1, 1))
        & (pl.col("reference_date") == date(2024, 1, 2))
    )
    assert row["years_to_maturity"][0] == pytest.approx(1095 / 365.25)
    assert validate_yield_curve_gold(curve).height == 5


def test_validate_yield_curve_gold_rejects_unknown_bond(silver: pl.DataFrame) -> None:
    """A gold só aceita os títulos simulados."""
    curve = build_yield_curve(silver).with_columns(pl.lit("Tesouro Selic").alias("bond_type"))
    with pytest.raises(DataValidationError):
        validate_yield_curve_gold(curve)


def test_clean_sgs_parses_dedups_and_drops_invalid() -> None:
    """Datas dd/mm/aaaa, valores numéricos; nulos e duplicatas são removidos."""
    raw = pl.DataFrame(
        {
            "data": ["02/01/2024", "01/01/2024", "01/01/2024", "03/01/2024"],
            "valor": ["0.04", "0.03", "0.03", ""],
        }
    )
    clean = clean_sgs(raw)
    assert clean["reference_date"].to_list() == [date(2024, 1, 1), date(2024, 1, 2)]
    assert clean["value"].to_list() == [0.03, 0.04]
    assert validate_macro_silver(clean, "selic").height == 2


def test_clean_sgs_requires_columns() -> None:
    """Sem 'data'/'valor' a limpeza falha."""
    with pytest.raises(DataValidationError):
        clean_sgs(pl.DataFrame({"x": ["1"]}))


def test_validate_macro_silver_rejects_out_of_range_and_duplicates() -> None:
    """Valores absurdos e datas repetidas violam o contrato."""
    base = pl.DataFrame({"reference_date": [date(2024, 1, 1)], "value": [0.5]})
    with pytest.raises(DataValidationError):
        validate_macro_silver(base.with_columns(pl.lit(999.0).alias("value")), "ipca")
    with pytest.raises(DataValidationError, match="duplicadas"):
        validate_macro_silver(pl.concat([base, base]), "ipca")

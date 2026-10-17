"""Fixtures compartilhadas: dados sintéticos pequenos e download simulado (sem rede)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from config.settings import PathsSettings, Settings
from constants.artifacts import GOLD_YIELD_CURVE, SILVER_IPCA, SILVER_SELIC
from data.reader import read_parquet
from pipelines.ingestion import run_ingestion
from pipelines.processing import run_processing

TESOURO_CSV = """Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha
Tesouro Prefixado;01/01/2027;02/01/2024;10,50;10,60;750,10;749,00;749,50
Tesouro Prefixado;01/01/2027;03/01/2024;10,40;10,50;752,10;751,00;751,50
Tesouro Prefixado;01/01/2029;02/01/2024;11,00;11,10;600,10;599,00;599,50
Tesouro IPCA+;15/05/2035;02/01/2024;6,00;6,10;2000,00;1990,00;1995,00
Tesouro IPCA+;15/05/2035;03/01/2024;6,05;6,15;1999,00;1989,00;1994,00
Tesouro Selic;01/03/2027;02/01/2024;0,05;0,06;14000,00;13990,00;13995,00
Tesouro Prefixado;01/07/2025;02/01/2024;;;;;
Tesouro Prefixado;01/12/2023;02/01/2024;9,00;9,10;990,00;989,00;989,50
Tesouro Prefixado;01/01/2027;02/01/2024;10,50;10,60;750,10;749,00;749,50
"""

SELIC_RECORDS = [
    {"data": "02/01/2024", "valor": "0.040"},
    {"data": "03/01/2024", "valor": "0.040"},
    {"data": "04/01/2024", "valor": "0.040"},
]

IPCA_RECORDS = [
    {"data": "01/01/2024", "valor": "0.42"},
    {"data": "01/02/2024", "valor": "0.83"},
]


class FakeFetcher:
    """Substitui o download HTTP: devolve conteúdo sintético e registra as URLs chamadas."""

    def __init__(self) -> None:
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        """Responde a URL do Tesouro com CSV e as do SGS com JSON."""
        self.urls.append(url)
        if "tesourotransparente" in url:
            return TESOURO_CSV.encode("utf-8")
        if "sgs.11/" in url:
            return json.dumps(SELIC_RECORDS).encode("utf-8")
        if "sgs.433/" in url:
            return json.dumps(IPCA_RECORDS).encode("utf-8")
        raise AssertionError(f"URL inesperada: {url}")


@pytest.fixture
def tesouro_csv() -> str:
    """CSV sintético no formato do Tesouro Transparente."""
    return TESOURO_CSV


@pytest.fixture
def fetcher() -> FakeFetcher:
    """Download simulado."""
    return FakeFetcher()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Configuração padrão com todas as camadas em um diretório temporário."""
    paths = PathsSettings(
        bronze=tmp_path / "bronze",
        silver=tmp_path / "silver",
        gold=tmp_path / "gold",
        reports=tmp_path / "reports",
        logs=tmp_path / "logs",
    )
    return Settings(paths=paths)


@pytest.fixture
def processed(
    settings: Settings, fetcher: FakeFetcher
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Executa ingestão + processamento sintéticos e devolve (curva, ipca, selic)."""
    run_ingestion(settings, fetch=fetcher, end_date=date(2024, 3, 31))
    run_processing(settings)
    return (
        read_parquet(settings.paths.gold / GOLD_YIELD_CURVE),
        read_parquet(settings.paths.silver / SILVER_IPCA),
        read_parquet(settings.paths.silver / SILVER_SELIC),
    )

"""Testes de integração do pipeline bronze -> silver -> gold -> gráficos (sem rede)."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl
import pytest
import yaml

from config.logging import configure_logging
from config.paths import CONFIGS_DIR
from config.settings import Settings
from constants.artifacts import GOLD_YIELD_CURVE, SILVER_IPCA, SILVER_SELIC, SILVER_TESOURO
from exceptions import DataNotFoundError
from main import main, parse_args
from pipelines.ingestion import run_ingestion
from pipelines.plots import run_plots, slugify_bond
from pipelines.processing import run_processing

END = date(2024, 3, 31)

pytestmark = pytest.mark.integration


def test_ingestion_is_idempotent_and_cached(settings: Settings, fetcher: Any) -> None:
    """A segunda execução (dentro do TTL) não faz nenhuma requisição."""
    paths = run_ingestion(settings, fetch=fetcher, end_date=END)
    assert set(paths) == {"tesouro", "selic_daily", "ipca_monthly"}
    assert all(path.is_file() for path in paths.values())
    calls_after_first = len(fetcher.urls)
    assert calls_after_first == 7  # 1 CSV + 3 janelas Selic + 3 janelas IPCA

    again = run_ingestion(settings, fetch=fetcher, end_date=END)
    assert again == paths
    assert len(fetcher.urls) == calls_after_first

    run_ingestion(settings, force=True, fetch=fetcher, end_date=END)
    assert len(fetcher.urls) == 2 * calls_after_first


def test_processing_builds_validated_silver_and_gold(settings: Settings, fetcher: Any) -> None:
    """Gera silver e gold válidas a partir da bronze, sem alterá-la."""
    run_ingestion(settings, fetch=fetcher, end_date=END)
    bronze_files = sorted(settings.paths.bronze.rglob("*"))
    outputs = run_processing(settings)

    assert outputs["silver_tesouro"] == settings.paths.silver / SILVER_TESOURO
    assert pl.read_parquet(settings.paths.silver / SILVER_SELIC).height == 3
    assert pl.read_parquet(settings.paths.silver / SILVER_IPCA).height == 2
    assert pl.read_parquet(settings.paths.gold / GOLD_YIELD_CURVE).height == 5
    assert sorted(settings.paths.bronze.rglob("*")) == bronze_files  # bronze imutável


def test_processing_without_bronze_fails_with_clear_error(settings: Settings) -> None:
    """Sem ingestão prévia, a mensagem orienta o usuário."""
    with pytest.raises(DataNotFoundError, match="ingestão"):
        run_processing(settings)


def test_plots_generate_one_html_per_bond(settings: Settings, processed: Any) -> None:
    """Gera um HTML interativo por título simulado."""
    outputs = run_plots(settings)
    assert {path.name for path in outputs} == {
        "yield_curve_tesouro_prefixado.html",
        "yield_curve_tesouro_ipca_mais.html",
    }
    assert all(path.stat().st_size > 0 for path in outputs)


def test_slugify_bond() -> None:
    """O slug é seguro para nome de arquivo."""
    assert slugify_bond("Tesouro IPCA+") == "tesouro_ipca_mais"
    assert slugify_bond("Tesouro Prefixado") == "tesouro_prefixado"


def test_cli_parse_args_defaults() -> None:
    """Argumentos padrão da linha de comando."""
    args = parse_args(["ingest", "--force"])
    assert args.command == "ingest"
    assert args.force is True
    assert args.log_level is None


def test_cli_returns_error_code_on_invalid_config(tmp_path: Path) -> None:
    """Configuração ausente resulta em código de saída 1 (sem traceback)."""
    assert main(["build", "--config-dir", str(tmp_path)]) == 1


def test_configure_logging_creates_daily_file(tmp_path: Path) -> None:
    """O arquivo de log é criado a partir do dictConfig e recebe mensagens."""
    config = yaml.safe_load((CONFIGS_DIR / "logging.yaml").read_text(encoding="utf-8"))
    config["handlers"]["file"]["filename"] = str(tmp_path / "logs" / "log.log")
    config_path = tmp_path / "logging.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    configure_logging(level="DEBUG", config_path=config_path)
    logging.getLogger("teste").info("mensagem de teste")
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    for handler in root.handlers[:]:
        handler.flush()
        handler.close()
        root.removeHandler(handler)
    files = list((tmp_path / "logs").glob("log*.log"))
    assert len(files) == 1
    assert "mensagem de teste" in files[0].read_text(encoding="utf-8")

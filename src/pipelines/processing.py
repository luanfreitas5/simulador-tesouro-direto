"""Pipeline de processamento: bronze -> silver -> gold, com contratos de dados."""

from __future__ import annotations

import logging
from pathlib import Path

from config.settings import Settings
from constants.artifacts import GOLD_YIELD_CURVE, SILVER_IPCA, SILVER_SELIC, SILVER_TESOURO
from data.bcb import sgs_filename, sgs_source_name
from data.downloader import get_latest_file
from data.reader import read_sgs_json, read_tesouro_csv
from data.tesouro import TESOURO_SOURCE
from data.writer import write_parquet
from features.yield_curve import build_yield_curve
from preprocessing.cleaning import clean_sgs, clean_tesouro
from schemas.macro import validate_macro_silver
from schemas.treasury import validate_tesouro_silver, validate_yield_curve_gold

logger = logging.getLogger(__name__)


def _process_sgs(settings: Settings, code: int, name: str, target: Path) -> Path:
    source = get_latest_file(settings.paths.bronze / sgs_source_name(code), sgs_filename(code))
    silver = validate_macro_silver(clean_sgs(read_sgs_json(source)), name)
    logger.info("Série %s: %d registros na silver.", name, silver.height)
    return write_parquet(silver, target)


def run_processing(settings: Settings) -> dict[str, Path]:
    """Gera as camadas silver e gold a partir do snapshot mais recente da bronze.

    Valida o contrato de dados na saída de cada etapa e nunca altera a bronze.

    Parameters
    ----------
    settings : Settings
        Configuração validada do projeto.

    Returns
    -------
    dict[str, Path]
        Arquivos gerados: ``silver_tesouro``, ``silver_selic``, ``silver_ipca`` e
        ``gold_yield_curve``.

    Raises
    ------
    DataNotFoundError
        Se a bronze ainda não existir (rode a ingestão antes).
    DataValidationError
        Se algum contrato de dados for violado.

    Examples
    --------
    >>> outputs = run_processing(load_settings())  # doctest: +SKIP
    """
    paths = settings.paths
    series = settings.ingestion.bcb.series

    csv_path = get_latest_file(paths.bronze / TESOURO_SOURCE, settings.ingestion.tesouro.filename)
    silver = validate_tesouro_silver(clean_tesouro(read_tesouro_csv(csv_path)))
    logger.info("Tesouro: %d registros na silver.", silver.height)
    outputs = {"silver_tesouro": write_parquet(silver, paths.silver / SILVER_TESOURO)}

    curve = validate_yield_curve_gold(build_yield_curve(silver))
    logger.info("Curva de juros: %d pontos na gold.", curve.height)
    outputs["gold_yield_curve"] = write_parquet(curve, paths.gold / GOLD_YIELD_CURVE)

    outputs["silver_selic"] = _process_sgs(
        settings, series.selic_daily, "selic_daily", paths.silver / SILVER_SELIC
    )
    outputs["silver_ipca"] = _process_sgs(
        settings, series.ipca_monthly, "ipca_monthly", paths.silver / SILVER_IPCA
    )
    return outputs

"""Pipeline de ingestão: Tesouro Transparente + Selic e IPCA (SGS/BCB) -> bronze."""

from __future__ import annotations

import logging
from datetime import date
from functools import partial
from pathlib import Path

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from config.settings import Settings
from data.bcb import ingest_sgs_series
from data.downloader import Fetcher, http_get
from data.tesouro import ingest_tesouro

logger = logging.getLogger(__name__)


def run_ingestion(
    settings: Settings,
    force: bool = False,
    fetch: Fetcher | None = None,
    end_date: date | None = None,
) -> dict[str, Path]:
    """Executa a ingestão idempotente das três fontes na camada bronze.

    Parameters
    ----------
    settings : Settings
        Configuração validada do projeto.
    force : bool, optional
        Ignora o cache local e baixa novamente, by default False.
    fetch : Fetcher | None, optional
        Função ``url -> bytes``; por padrão, HTTP GET (injetável para testes).
    end_date : date | None, optional
        Data final das séries do SGS; por padrão, hoje.

    Returns
    -------
    dict[str, Path]
        Caminho de cada arquivo bronze: ``tesouro``, ``selic_daily``, ``ipca_monthly``.

    Raises
    ------
    DataIngestionError
        Se algum download falhar e não houver cópia local.

    Examples
    --------
    >>> paths = run_ingestion(load_settings())  # doctest: +SKIP
    """
    ingestion = settings.ingestion
    fetcher = fetch or partial(
        http_get, timeout_seconds=ingestion.timeout_seconds, user_agent=ingestion.user_agent
    )
    end = end_date or date.today()
    bronze = settings.paths.bronze
    series = ingestion.bcb.series

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )
    paths: dict[str, Path] = {}
    with progress:
        task = progress.add_task("Ingestão (bronze)", total=3)
        paths["tesouro"] = ingest_tesouro(ingestion, bronze, fetcher, force)
        progress.advance(task)
        paths["selic_daily"] = ingest_sgs_series(
            series.selic_daily, ingestion, bronze, fetcher, end, force
        )
        progress.advance(task)
        paths["ipca_monthly"] = ingest_sgs_series(
            series.ipca_monthly, ingestion, bronze, fetcher, end, force
        )
        progress.advance(task)
    logger.info("Ingestão concluída: %s", {name: str(path) for name, path in paths.items()})
    return paths

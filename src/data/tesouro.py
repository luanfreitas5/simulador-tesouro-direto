"""Ingestão do CSV de preços e taxas do Tesouro Direto (Tesouro Transparente)."""

from __future__ import annotations

from pathlib import Path

from config.settings import IngestionSettings
from data.downloader import Fetcher, ensure_snapshot

TESOURO_SOURCE = "tesouro_transparente"


def ingest_tesouro(
    settings: IngestionSettings, bronze_dir: Path, fetch: Fetcher, force: bool = False
) -> Path:
    """Baixa (ou reutiliza do cache) o CSV do Tesouro Transparente na camada bronze.

    Parameters
    ----------
    settings : IngestionSettings
        Parâmetros de ingestão (URL, nome do arquivo, TTL do cache).
    bronze_dir : Path
        Diretório da camada bronze.
    fetch : Fetcher
        Função ``url -> bytes`` que realiza o download.
    force : bool, optional
        Ignora o cache, by default False.

    Returns
    -------
    Path
        Caminho do CSV no snapshot vigente.

    Raises
    ------
    DataIngestionError
        Se o download falhar e não houver cópia local.
    """
    url = settings.tesouro.url
    return ensure_snapshot(
        source_dir=bronze_dir / TESOURO_SOURCE,
        filename=settings.tesouro.filename,
        fetch=lambda: fetch(url),
        url=url,
        ttl_hours=settings.cache_ttl_hours,
        force=force,
    )

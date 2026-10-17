"""Ingestão de séries temporais do SGS (Sistema Gerenciador de Séries do Banco Central)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from config.settings import IngestionSettings
from data.downloader import Fetcher, ensure_snapshot
from exceptions import DataIngestionError


def sgs_source_name(code: int) -> str:
    """Nome do diretório da série na camada bronze.

    Parameters
    ----------
    code : int
        Código da série no SGS.

    Returns
    -------
    str
        Nome do diretório (``bcb_sgs_<código>``).
    """
    return f"bcb_sgs_{code}"


def sgs_filename(code: int) -> str:
    """Nome do arquivo JSON da série dentro do snapshot.

    Parameters
    ----------
    code : int
        Código da série no SGS.

    Returns
    -------
    str
        Nome do arquivo (``serie_<código>.json``).
    """
    return f"serie_{code}.json"


def build_sgs_url(base_url: str, code: int, start: date, end: date) -> str:
    """Monta a URL da API de dados abertos do SGS para uma janela de datas.

    Parameters
    ----------
    base_url : str
        URL base (``https://api.bcb.gov.br/dados/serie``).
    code : int
        Código da série.
    start : date
        Data inicial (inclusiva).
    end : date
        Data final (inclusiva).

    Returns
    -------
    str
        URL completa da consulta em JSON.

    Examples
    --------
    >>> build_sgs_url("http://x", 433, date(2020, 1, 1), date(2020, 12, 31))
    'http://x/bcdata.sgs.433/dados?formato=json&dataInicial=01/01/2020&dataFinal=31/12/2020'
    """
    return (
        f"{base_url}/bcdata.sgs.{code}/dados?formato=json"
        f"&dataInicial={start:%d/%m/%Y}&dataFinal={end:%d/%m/%Y}"
    )


def split_date_windows(start: date, end: date, max_years: int) -> list[tuple[date, date]]:
    """Divide ``[start, end]`` em janelas de anos-calendário de até ``max_years`` anos.

    A API do SGS limita consultas de séries diárias a janelas de 10 anos.

    Parameters
    ----------
    start : date
        Data inicial.
    end : date
        Data final.
    max_years : int
        Máximo de anos-calendário por janela (>= 1).

    Returns
    -------
    list[tuple[date, date]]
        Janelas contíguas e sem sobreposição (vazia se ``end < start``).

    Examples
    --------
    >>> windows = split_date_windows(date(2002, 1, 1), date(2012, 6, 30), 9)
    >>> [(a.isoformat(), b.isoformat()) for a, b in windows]
    [('2002-01-01', '2010-12-31'), ('2011-01-01', '2012-06-30')]
    """
    windows: list[tuple[date, date]] = []
    current = start
    while current <= end:
        window_end = min(date(current.year + max_years - 1, 12, 31), end)
        windows.append((current, window_end))
        current = window_end + timedelta(days=1)
    return windows


def fetch_sgs_series(
    code: int, start: date, end: date, base_url: str, max_window_years: int, fetch: Fetcher
) -> bytes:
    """Baixa uma série do SGS em janelas e devolve o JSON concatenado (sem duplicatas).

    Parameters
    ----------
    code : int
        Código da série.
    start : date
        Data inicial.
    end : date
        Data final.
    base_url : str
        URL base da API.
    max_window_years : int
        Tamanho máximo da janela em anos-calendário.
    fetch : Fetcher
        Função ``url -> bytes``.

    Returns
    -------
    bytes
        JSON (lista de ``{"data", "valor"}``) com todos os registros.

    Raises
    ------
    DataIngestionError
        Se alguma resposta não for uma lista JSON válida.
    """
    records: dict[str, dict[str, str]] = {}
    for window_start, window_end in split_date_windows(start, end, max_window_years):
        url = build_sgs_url(base_url, code, window_start, window_end)
        try:
            payload = json.loads(fetch(url))
        except json.JSONDecodeError as exc:
            raise DataIngestionError(f"Resposta inválida do SGS para a série {code}.") from exc
        if not isinstance(payload, list):
            raise DataIngestionError(f"Resposta inesperada do SGS para a série {code}: {payload}")
        for record in payload:
            records[record["data"]] = record
    return json.dumps(list(records.values()), ensure_ascii=False).encode("utf-8")


def ingest_sgs_series(
    code: int,
    settings: IngestionSettings,
    bronze_dir: Path,
    fetch: Fetcher,
    end: date,
    force: bool = False,
) -> Path:
    """Baixa (ou reutiliza do cache) uma série do SGS na camada bronze.

    Parameters
    ----------
    code : int
        Código da série.
    settings : IngestionSettings
        Parâmetros de ingestão.
    bronze_dir : Path
        Diretório da camada bronze.
    fetch : Fetcher
        Função ``url -> bytes``.
    end : date
        Data final da consulta.
    force : bool, optional
        Ignora o cache, by default False.

    Returns
    -------
    Path
        Caminho do JSON no snapshot vigente.

    Raises
    ------
    DataIngestionError
        Se o download falhar e não houver cópia local.
    """
    bcb = settings.bcb
    return ensure_snapshot(
        source_dir=bronze_dir / sgs_source_name(code),
        filename=sgs_filename(code),
        fetch=lambda: fetch_sgs_series(
            code, bcb.start_date, end, bcb.base_url, bcb.max_window_years, fetch
        ),
        url=build_sgs_url(bcb.base_url, code, bcb.start_date, end),
        ttl_hours=settings.cache_ttl_hours,
        force=force,
    )

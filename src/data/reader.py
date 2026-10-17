"""Leitura de arquivos brutos (bronze) e de parquet (silver/gold)."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

from exceptions import DataIngestionError, DataNotFoundError


def read_tesouro_csv(path: Path) -> pl.DataFrame:
    """Lê o CSV do Tesouro Transparente sem inferir tipos (tudo como texto).

    Parameters
    ----------
    path : Path
        Caminho do CSV (separador ``;``, decimal com vírgula).

    Returns
    -------
    pl.DataFrame
        DataFrame bruto com colunas de texto.

    Raises
    ------
    DataNotFoundError
        Se o arquivo não existir.
    """
    if not path.is_file():
        raise DataNotFoundError(f"Arquivo não encontrado: {path}")
    return pl.read_csv(path, separator=";", infer_schema=False, encoding="utf8-lossy")


def read_sgs_json(path: Path) -> pl.DataFrame:
    """Lê o JSON de uma série do SGS (colunas ``data`` e ``valor`` como texto).

    Parameters
    ----------
    path : Path
        Caminho do JSON.

    Returns
    -------
    pl.DataFrame
        DataFrame com as colunas ``data`` e ``valor`` (texto).

    Raises
    ------
    DataNotFoundError
        Se o arquivo não existir.
    DataIngestionError
        Se o conteúdo não for uma lista JSON.
    """
    if not path.is_file():
        raise DataNotFoundError(f"Arquivo não encontrado: {path}")
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DataIngestionError(f"JSON inválido em {path}") from exc
    if not isinstance(records, list):
        raise DataIngestionError(f"O arquivo {path} deve conter uma lista de registros.")
    schema = {"data": pl.String, "valor": pl.String}
    return pl.DataFrame(records, schema=schema)


def read_parquet(path: Path) -> pl.DataFrame:
    """Lê um arquivo parquet.

    Parameters
    ----------
    path : Path
        Caminho do arquivo.

    Returns
    -------
    pl.DataFrame
        Conteúdo do arquivo.

    Raises
    ------
    DataNotFoundError
        Se o arquivo não existir (rode ``make pipeline``).
    """
    if not path.is_file():
        raise DataNotFoundError(f"Arquivo não encontrado: {path}. Execute o pipeline primeiro.")
    return pl.read_parquet(path)

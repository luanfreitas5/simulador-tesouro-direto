"""Escrita de dados nas camadas silver e gold."""

from __future__ import annotations

from pathlib import Path

import polars as pl


def write_parquet(df: pl.DataFrame, path: Path) -> Path:
    """Grava um DataFrame em parquet, criando os diretórios necessários.

    Parameters
    ----------
    df : pl.DataFrame
        Dados a gravar.
    path : Path
        Caminho de destino.

    Returns
    -------
    Path
        O próprio caminho de destino.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    return path

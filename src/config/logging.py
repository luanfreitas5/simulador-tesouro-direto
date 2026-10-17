"""Configuração de logging com handler Rich (console) e arquivo com rotação diária."""

from __future__ import annotations

import logging
from datetime import date
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

FILE_FORMAT = "%(asctime)s \t %(levelname)s \t %(name)s \t %(message)s"


def configure_logging(
    level: str = "INFO", log_dir: Path | None = None, retention_days: int = 30
) -> None:
    """Configura o logging global do projeto.

    Parameters
    ----------
    level : str, optional
        Nível de log (``DEBUG``, ``INFO``...), by default ``"INFO"``.
    log_dir : Path | None, optional
        Diretório dos arquivos ``log_YYYY-MM-DD.log``; ``None`` desativa o arquivo.
    retention_days : int, optional
        Quantidade de arquivos rotacionados mantidos, by default 30.

    Examples
    --------
    >>> configure_logging("INFO", Path("logs"))
    """
    handlers: list[logging.Handler] = [RichHandler(rich_tracebacks=True, show_path=False)]
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            log_dir / f"log_{date.today():%Y-%m-%d}.log",
            when="midnight",
            backupCount=retention_days,
            encoding="utf-8",
        )
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        handlers.append(file_handler)
    logging.basicConfig(
        level=level,
        format="%(name)s \t %(message)s",
        datefmt="[%X]",
        handlers=handlers,
        force=True,
    )

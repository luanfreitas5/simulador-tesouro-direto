"""Orquestração do pipeline: ingestão (bronze), processamento (silver/gold) e gráficos.

Uso::

    uv run python src/main.py ingest [--force]
    uv run python src/main.py build
    uv run python src/main.py plots
    uv run python src/main.py all [--force]
"""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from config.logging import configure_logging
from config.paths import CONFIGS_DIR
from config.settings import Settings, load_settings
from exceptions import TesouroError
from pipelines.ingestion import run_ingestion
from pipelines.plots import run_plots
from pipelines.processing import run_processing

logger = logging.getLogger(__name__)

COMMANDS = ("ingest", "build", "plots", "all")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Interpreta os argumentos de linha de comando.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Argumentos (por padrão, ``sys.argv[1:]``).

    Returns
    -------
    argparse.Namespace
        Argumentos interpretados (``command``, ``force``, ``config_dir``, ``log_level``).
    """
    parser = argparse.ArgumentParser(description="Pipeline do simulador do Tesouro Direto.")
    parser.add_argument("command", choices=COMMANDS, help="etapa a executar")
    parser.add_argument("--force", action="store_true", help="ignora o cache local da ingestão")
    parser.add_argument("--config-dir", type=Path, default=CONFIGS_DIR, help="pasta dos YAML")
    parser.add_argument("--log-level", default=None, help="sobrescreve o nível do logging.yaml")
    return parser.parse_args(argv)


def run(command: str, settings: Settings, force: bool = False) -> None:
    """Executa a etapa pedida.

    Parameters
    ----------
    command : str
        Uma de ``ingest``, ``build``, ``plots`` ou ``all``.
    settings : Settings
        Configuração validada.
    force : bool, optional
        Ignora o cache da ingestão, by default False.
    """
    if command in ("ingest", "all"):
        run_ingestion(settings, force=force)
    if command in ("build", "all"):
        run_processing(settings)
    if command in ("plots", "all"):
        run_plots(settings)


def main(argv: Sequence[str] | None = None) -> int:
    """Ponto de entrada da linha de comando.

    Parameters
    ----------
    argv : Sequence[str] | None, optional
        Argumentos (por padrão, ``sys.argv[1:]``).

    Returns
    -------
    int
        Código de saída: 0 em sucesso, 1 em erro conhecido do projeto.
    """
    args = parse_args(argv)
    try:
        settings = load_settings(args.config_dir)
        configure_logging(level=args.log_level, config_path=args.config_dir / "logging.yaml")
        run(args.command, settings, force=args.force)
    except TesouroError:
        logger.exception("Execução interrompida")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Geração dos gráficos HTML da curva de juros navegável por data."""

from __future__ import annotations

import logging
from pathlib import Path

from config.settings import Settings
from constants.artifacts import FIGURE_YIELD_CURVE_TEMPLATE, GOLD_YIELD_CURVE
from constants.bonds import SIMULATED_BONDS
from data.reader import read_parquet
from visualization.yield_curve import plot_yield_curve_slider

logger = logging.getLogger(__name__)


def slugify_bond(bond_type: str) -> str:
    """Converte o nome de um título em sufixo de arquivo.

    Parameters
    ----------
    bond_type : str
        Nome do título (``"Tesouro IPCA+"``).

    Returns
    -------
    str
        Texto em minúsculas, sem espaços (``"tesouro_ipca_mais"``).

    Examples
    --------
    >>> slugify_bond("Tesouro IPCA+")
    'tesouro_ipca_mais'
    """
    return bond_type.lower().replace("+", "_mais").replace(" ", "_")


def run_plots(settings: Settings) -> list[Path]:
    """Gera um HTML interativo (slider por data) para cada título simulado.

    Parameters
    ----------
    settings : Settings
        Configuração validada do projeto.

    Returns
    -------
    list[Path]
        Arquivos HTML gerados em ``reports/figures/``.

    Raises
    ------
    DataNotFoundError
        Se a camada gold ainda não existir (rode o processamento antes).
    """
    curve = read_parquet(settings.paths.gold / GOLD_YIELD_CURVE)
    figures_dir = settings.paths.reports / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for bond_type in SIMULATED_BONDS:
        target = figures_dir / FIGURE_YIELD_CURVE_TEMPLATE.format(slug=slugify_bond(bond_type))
        plot_yield_curve_slider(curve, bond_type).write_html(target, include_plotlyjs="cdn")
        logger.info("Gráfico gerado: %s", target)
        outputs.append(target)
    return outputs

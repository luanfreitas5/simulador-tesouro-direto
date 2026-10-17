"""Gráficos da curva de juros: uma data específica ou navegável por data (slider)."""

from __future__ import annotations

from datetime import date

import numpy as np
import plotly.graph_objects as go
import polars as pl

from exceptions import DataNotFoundError
from visualization.theme import PALETTE, apply_theme

X_TITLE = "Prazo até o vencimento (anos)"
Y_TITLE = "Taxa de compra (% a.a.)"


def _scatter(frame: pl.DataFrame, bond_type: str) -> go.Scatter:
    ordered = frame.sort("years_to_maturity")
    return go.Scatter(
        x=ordered["years_to_maturity"].to_list(),
        y=ordered["buy_rate"].to_list(),
        mode="lines+markers",
        line={"color": PALETTE.get(bond_type, "#444444")},
        text=[f"Venc.: {d:%d/%m/%Y}" for d in ordered["maturity_date"].to_list()],
        hovertemplate="%{text}<br>Prazo: %{x:.2f} anos<br>Taxa: %{y:.2f}% a.a.<extra></extra>",
        name=bond_type,
    )


def plot_curve_for_date(curve: pl.DataFrame, bond_type: str, reference_date: date) -> go.Figure:
    """Plota a curva de juros de um título em uma data de referência exata.

    Parameters
    ----------
    curve : pl.DataFrame
        Curva de juros (camada gold).
    bond_type : str
        Título (Prefixado ou IPCA+).
    reference_date : date
        Data de referência com cotação disponível.

    Returns
    -------
    go.Figure
        Figura com a taxa de compra por prazo até o vencimento.

    Raises
    ------
    DataNotFoundError
        Se não houver cotação do título na data.
    """
    frame = curve.filter(
        (pl.col("bond_type") == bond_type) & (pl.col("reference_date") == reference_date)
    )
    if frame.height == 0:
        raise DataNotFoundError(f"Sem cotação de '{bond_type}' em {reference_date}.")
    fig = go.Figure(_scatter(frame, bond_type))
    fig.update_xaxes(title=X_TITLE)
    fig.update_yaxes(title=Y_TITLE)
    return apply_theme(fig, f"{bond_type} — curva de juros em {reference_date:%d/%m/%Y}")


def _sample_evenly(items: list[date], limit: int) -> list[date]:
    """Reduz ``items`` a no máximo ``limit`` elementos igualmente espaçados (inclui o último)."""
    if len(items) <= limit:
        return items
    positions = np.unique(np.linspace(0, len(items) - 1, limit).round().astype(int))
    return [items[i] for i in positions]


def plot_yield_curve_slider(
    curve: pl.DataFrame, bond_type: str, max_frames: int = 250
) -> go.Figure:
    """Plota a curva de juros navegável por data (slider + animação do Plotly).

    Os eixos são fixos (mesma escala em todas as datas) e o número de quadros é
    limitado a ``max_frames`` datas igualmente espaçadas, mantendo o HTML leve.

    Parameters
    ----------
    curve : pl.DataFrame
        Curva de juros (camada gold).
    bond_type : str
        Título (Prefixado ou IPCA+).
    max_frames : int, optional
        Máximo de datas navegáveis, by default 250.

    Returns
    -------
    go.Figure
        Figura com slider por data, iniciando na data mais recente.

    Raises
    ------
    DataNotFoundError
        Se não houver dados para o título.

    Examples
    --------
    >>> fig = plot_yield_curve_slider(curve, "Tesouro Prefixado")  # doctest: +SKIP
    >>> fig.write_html("curva.html")  # doctest: +SKIP
    """
    data = curve.filter(pl.col("bond_type") == bond_type)
    if data.height == 0:
        raise DataNotFoundError(f"Sem dados de curva para '{bond_type}'.")

    partitions = data.partition_by("reference_date", as_dict=True)
    parts = {key[0]: part for key, part in partitions.items()}
    dates = _sample_evenly(sorted(parts), max_frames)
    frames = [go.Frame(data=[_scatter(parts[d], bond_type)], name=d.isoformat()) for d in dates]
    steps = [
        {
            "method": "animate",
            "label": d.strftime("%m/%Y"),
            "args": [
                [d.isoformat()],
                {"mode": "immediate", "frame": {"duration": 0, "redraw": True}},
            ],
        }
        for d in dates
    ]

    max_years = float(data.select(pl.col("years_to_maturity").max()).item())
    min_rate = float(data.select(pl.col("buy_rate").min()).item())
    max_rate = float(data.select(pl.col("buy_rate").max()).item())

    fig = go.Figure(data=frames[-1].data, frames=frames)
    fig.update_xaxes(title=X_TITLE, range=[0, max_years * 1.05])
    fig.update_yaxes(title=Y_TITLE, range=[min_rate - 1, max_rate + 1])
    fig.update_layout(
        sliders=[{"active": len(steps) - 1, "steps": steps, "currentvalue": {"prefix": "Data: "}}]
    )
    return apply_theme(fig, f"{bond_type} — curva de juros por data")

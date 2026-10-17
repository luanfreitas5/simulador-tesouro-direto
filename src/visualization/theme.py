"""Tema visual compartilhado entre os gráficos."""

from __future__ import annotations

import plotly.graph_objects as go

PALETTE: dict[str, str] = {
    "Tesouro Prefixado": "#1f77b4",
    "Tesouro IPCA+": "#d95f02",
    "positive": "#2a9d8f",
    "negative": "#c0392b",
    "total": "#264653",
}


def apply_theme(fig: go.Figure, title: str) -> go.Figure:
    """Aplica título, fonte e fundo padronizados a uma figura.

    Parameters
    ----------
    fig : go.Figure
        Figura Plotly.
    title : str
        Título do gráfico.

    Returns
    -------
    go.Figure
        A mesma figura, com o tema aplicado.
    """
    fig.update_layout(
        title=title,
        template="plotly_white",
        font={"family": "Arial, sans-serif", "size": 13},
        margin={"l": 60, "r": 20, "t": 60, "b": 50},
    )
    return fig

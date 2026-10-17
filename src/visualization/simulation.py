"""Gráfico do resultado da simulação."""

from __future__ import annotations

import plotly.graph_objects as go

from finance.simulation import SimulationResult
from visualization.theme import PALETTE, apply_theme


def plot_net_waterfall(result: SimulationResult) -> go.Figure:
    """Plota a cascata do valor investido até o valor líquido final.

    Parameters
    ----------
    result : SimulationResult
        Resultado da simulação.

    Returns
    -------
    go.Figure
        Cascata: investido, rendimento bruto, IR, custódia e líquido final.

    Examples
    --------
    >>> fig = plot_net_waterfall(simulate_from_growth(1000.0, 1.1, 365))  # doctest: +SKIP
    """
    fig = go.Figure(
        go.Waterfall(
            x=["Investido", "Rendimento bruto", "IR", "Custódia", "Líquido final"],
            y=[
                result.invested,
                result.gross_profit,
                -result.ir_amount,
                -result.custody_cost,
                result.net_final,
            ],
            measure=["absolute", "relative", "relative", "relative", "total"],
            increasing={"marker": {"color": PALETTE["positive"]}},
            decreasing={"marker": {"color": PALETTE["negative"]}},
            totals={"marker": {"color": PALETTE["total"]}},
        )
    )
    fig.update_yaxes(title="Valor (R$)")
    return apply_theme(fig, "Do valor investido ao líquido final")

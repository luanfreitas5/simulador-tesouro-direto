"""Aplicativo Streamlit: curva de juros histórica e simulador do Tesouro Direto.

Execute com ``make app`` (requer ``make install-app`` e ``make pipeline``).
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # `src/` é a raiz de importação do projeto

import polars as pl
import streamlit as st

from config.settings import Settings, load_settings
from constants.artifacts import GOLD_YIELD_CURVE, SILVER_IPCA, SILVER_SELIC
from constants.bonds import SIMULATED_BONDS
from data.reader import read_parquet
from exceptions import TesouroError
from finance.parameters import TaxParams
from pipelines.simulation import (
    SimulationRequest,
    find_quote_date,
    list_available_maturities,
    run_simulation,
)
from utils.formatting import format_brl, format_percent
from visualization.simulation import plot_net_waterfall
from visualization.yield_curve import plot_curve_for_date, plot_yield_curve_slider

st.set_page_config(page_title="Simulador Tesouro Direto", page_icon="📈", layout="wide")


@st.cache_data(show_spinner="Carregando dados...")
def load_data(gold_dir: str, silver_dir: str) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    """Carrega a curva (gold) e as séries IPCA/Selic (silver) com cache do Streamlit."""
    curve = read_parquet(Path(gold_dir) / GOLD_YIELD_CURVE)
    ipca = read_parquet(Path(silver_dir) / SILVER_IPCA)
    selic = read_parquet(Path(silver_dir) / SILVER_SELIC)
    return curve, ipca, selic


def render_sidebar(settings: Settings) -> tuple[TaxParams, float, float]:
    """Desenha a barra lateral com as premissas editáveis e devolve seus valores."""
    base = settings.finance
    st.sidebar.header("Premissas")
    st.sidebar.warning(
        "Alíquotas e taxas mudam por regulamentação. **Confira as regras vigentes** "
        "(Tesouro Direto, B3 e Receita Federal) antes de usar os resultados."
    )
    projected_ipca = st.sidebar.number_input(
        "IPCA projetado (% a.a.)", value=base.projected_ipca_annual * 100, step=0.25
    )
    projected_selic = st.sidebar.number_input(
        "Selic projetada (% a.a.)", value=base.projected_selic_annual * 100, step=0.25
    )
    with st.sidebar.expander("Alíquotas e taxas (configuráveis)"):
        brackets = tuple(
            (
                bracket.max_days,
                st.number_input(
                    f"IR até {bracket.max_days} dias (%)",
                    value=bracket.rate * 100,
                    min_value=0.0,
                    max_value=100.0,
                    step=0.5,
                    key=f"ir_{bracket.max_days}",
                )
                / 100,
            )
            for bracket in base.ir_brackets
        )
        floor = st.number_input(
            "IR acima da última faixa (%)",
            value=base.ir_floor_rate * 100,
            min_value=0.0,
            max_value=100.0,
            step=0.5,
        )
        custody = st.number_input(
            "Taxa de custódia B3 (% a.a.)",
            value=base.custody_fee_annual * 100,
            min_value=0.0,
            max_value=10.0,
            step=0.05,
        )
    params = TaxParams(
        ir_brackets=brackets,
        ir_floor_rate=floor / 100,
        custody_fee_annual=custody / 100,
        business_days_per_year=base.business_days_per_year,
    )
    return params, projected_ipca / 100, projected_selic / 100


def render_curve_tab(curve: pl.DataFrame, min_date: date, max_date: date) -> None:
    """Aba da curva de juros: escolha de data e comparação entre os títulos."""
    chosen = st.slider(
        "Data de referência",
        min_value=min_date,
        max_value=max_date,
        value=max_date,
        format="DD/MM/YYYY",
    )
    columns = st.columns(len(SIMULATED_BONDS))
    for column, bond_type in zip(columns, SIMULATED_BONDS, strict=True):
        with column:
            try:
                quote = find_quote_date(curve, bond_type, chosen, max_gap_days=30)
                st.plotly_chart(plot_curve_for_date(curve, bond_type, quote), width="stretch")
            except TesouroError as exc:
                st.info(str(exc))
    with st.expander("Evolução no tempo (slider animado)"):
        bond_type = st.selectbox("Título", SIMULATED_BONDS, key="slider_bond")
        st.plotly_chart(plot_yield_curve_slider(curve, bond_type), width="stretch")


def render_simulator_tab(
    curve: pl.DataFrame,
    ipca: pl.DataFrame,
    selic: pl.DataFrame,
    params: TaxParams,
    projections: tuple[float, float],
    max_date: date,
) -> None:
    """Aba do simulador: formulário, métricas e cascata do resultado."""
    left, right = st.columns(2)
    bond_type = left.selectbox("Título", SIMULATED_BONDS)
    purchase_date = right.date_input("Data de compra", value=max_date, max_value=max_date)
    amount = left.number_input("Valor investido (R$)", min_value=30.0, value=10_000.0, step=100.0)
    try:
        maturities = list_available_maturities(curve, bond_type, purchase_date)
    except TesouroError as exc:
        st.warning(str(exc))
        return
    maturity = right.selectbox("Vencimento", maturities, format_func=lambda d: f"{d:%d/%m/%Y}")

    request = SimulationRequest(
        bond_type, purchase_date, amount, maturity, projections[0], projections[1]
    )
    try:
        outcome = run_simulation(request, curve, ipca, selic, params)
    except TesouroError as exc:
        st.error(str(exc))
        return

    result, benchmark = outcome.result, outcome.benchmark
    st.caption(
        f"Cotação de {outcome.quote_date:%d/%m/%Y}: {format_percent(outcome.annual_rate)} a.a. "
        f"| {outcome.business_days} dias úteis | {result.holding_days} dias corridos"
    )
    cols = st.columns(4)
    cols[0].metric("Valor bruto final", format_brl(result.gross_final))
    cols[1].metric("Valor líquido final", format_brl(result.net_final))
    cols[2].metric("Rentab. líquida a.a.", format_percent(result.net_annualized))
    cols[3].metric("Rentab. real a.a.", format_percent(result.real_annualized))

    st.plotly_chart(plot_net_waterfall(result), width="stretch")
    st.subheader("Comparação com a Selic (mesmo valor e prazo)")
    st.table(
        {
            "": ["Líquido final", "Líquida a.a.", "Real a.a."],
            bond_type: [
                format_brl(result.net_final),
                format_percent(result.net_annualized),
                format_percent(result.real_annualized),
            ],
            "Selic": [
                format_brl(benchmark.net_final),
                format_percent(benchmark.net_annualized),
                format_percent(benchmark.real_annualized),
            ],
        }
    )
    st.caption(
        f"IR aplicado: {format_percent(result.ir_rate)} sobre o rendimento "
        f"({format_brl(result.ir_amount)}); custódia estimada: {format_brl(result.custody_cost)}; "
        f"inflação acumulada: {format_percent(result.inflation_factor - 1)}."
    )


def main() -> None:
    """Monta a página."""
    st.title("📈 Simulador do Tesouro Direto")
    st.caption(
        "Curva de juros histórica e rentabilidade bruta, líquida e real. Projeto educacional: "
        "não é recomendação de investimento."
    )
    settings = load_settings()
    try:
        curve, ipca, selic = load_data(str(settings.paths.gold), str(settings.paths.silver))
    except TesouroError as exc:
        st.error(f"{exc}\n\nExecute `make pipeline` para gerar os dados.")
        return

    params, projected_ipca, projected_selic = render_sidebar(settings)
    min_date: date = curve.select(pl.col("reference_date").min()).item()
    max_date: date = curve.select(pl.col("reference_date").max()).item()
    curve_tab, simulator_tab = st.tabs(["Curva de juros", "Simulador"])
    with curve_tab:
        render_curve_tab(curve, min_date, max_date)
    with simulator_tab:
        projections = (projected_ipca, projected_selic)
        render_simulator_tab(curve, ipca, selic, params, projections, max_date)


main()

"""Testes das figuras Plotly, da formatação pt-BR, dos hashes e da configuração."""

from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

import plotly.graph_objects as go
import polars as pl
import pytest

from config.paths import CONFIGS_DIR
from config.settings import load_settings
from exceptions import ConfigurationError, DataNotFoundError
from finance.simulation import simulate_from_growth
from utils.formatting import format_brl, format_percent
from utils.hashing import hash_bytes, hash_file
from visualization.simulation import plot_net_waterfall
from visualization.yield_curve import plot_curve_for_date, plot_yield_curve_slider

BOND = "Tesouro Prefixado"


@pytest.fixture
def many_dates_curve() -> pl.DataFrame:
    """Curva sintética com 10 datas e 2 vencimentos por data."""
    rows = []
    for i in range(10):
        reference = date(2024, 1, 1) + timedelta(days=i)
        for years, maturity in ((1.0, date(2025, 1, 1)), (3.0, date(2027, 1, 1))):
            rows.append(
                {
                    "reference_date": reference,
                    "bond_type": BOND,
                    "maturity_date": maturity,
                    "years_to_maturity": years,
                    "buy_rate": 10.0 + i * 0.1 + years * 0.2,
                    "sell_rate": 10.0,
                }
            )
    return pl.DataFrame(rows)


def test_plot_curve_for_date(many_dates_curve: pl.DataFrame) -> None:
    """A figura de uma data tem um traço com os dois vencimentos."""
    fig = plot_curve_for_date(many_dates_curve, BOND, date(2024, 1, 3))
    assert isinstance(fig, go.Figure)
    assert len(list(fig.data[0]["x"])) == 2
    with pytest.raises(DataNotFoundError):
        plot_curve_for_date(many_dates_curve, BOND, date(2030, 1, 1))


def test_slider_has_one_frame_per_date_and_starts_at_latest(many_dates_curve: pl.DataFrame) -> None:
    """Navegável por data: um quadro por data, iniciando na mais recente."""
    fig = plot_yield_curve_slider(many_dates_curve, BOND)
    assert len(fig.frames) == 10
    assert fig.frames[-1].name == "2024-01-10"
    assert fig.layout.sliders[0].active == 9


def test_slider_limits_frames_and_keeps_extremes(many_dates_curve: pl.DataFrame) -> None:
    """Com max_frames menor que o total, amostra datas incluindo a primeira e a última."""
    fig = plot_yield_curve_slider(many_dates_curve, BOND, max_frames=3)
    names = [frame.name for frame in fig.frames]
    assert len(names) == 3
    assert names[0] == "2024-01-01"
    assert names[-1] == "2024-01-10"
    with pytest.raises(DataNotFoundError):
        plot_yield_curve_slider(many_dates_curve, "Tesouro IPCA+")


def test_waterfall_has_five_steps() -> None:
    """Cascata: investido, rendimento, IR, custódia e líquido."""
    fig = plot_net_waterfall(simulate_from_growth(1000.0, 1.1, 365))
    assert list(fig.data[0]["x"]) == [
        "Investido",
        "Rendimento bruto",
        "IR",
        "Custódia",
        "Líquido final",
    ]


def test_formatting_ptbr() -> None:
    """Separadores brasileiros e sinal negativo."""
    assert format_brl(1234.5) == "R$ 1.234,50"
    assert format_brl(-10) == "-R$ 10,00"
    assert format_brl(-0.001) == "R$ 0,00"
    assert format_percent(0.1234) == "12,34%"
    assert format_percent(-0.05, decimals=1) == "-5,0%"


def test_hashing(tmp_path: Path) -> None:
    """hash_bytes e hash_file concordam e seguem o SHA-256 conhecido da string vazia."""
    assert hash_bytes(b"").startswith("e3b0c442")
    target = tmp_path / "a.bin"
    target.write_bytes(b"conteudo")
    assert hash_file(target) == hash_bytes(b"conteudo")


def test_load_real_settings() -> None:
    """Os YAML do repositório são válidos e os caminhos são resolvidos."""
    settings = load_settings()
    assert settings.finance.custody_fee_annual == 0.002
    assert [b.max_days for b in settings.finance.ir_brackets] == [180, 360, 720]
    assert settings.paths.bronze.is_absolute()
    assert settings.ingestion.bcb.series.ipca_monthly == 433


def test_invalid_config_fails_at_startup(tmp_path: Path) -> None:
    """Valor fora do intervalo e arquivo ausente falham com ConfigurationError."""
    shutil.copytree(CONFIGS_DIR, tmp_path / "cfg")
    finance = tmp_path / "cfg" / "finance.yaml"
    finance.write_text("finance:\n  custody_fee_annual: 5\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_settings(tmp_path / "cfg")
    finance.unlink()
    with pytest.raises(ConfigurationError, match="não encontrado"):
        load_settings(tmp_path / "cfg")


def test_unknown_config_key_and_bad_yaml_are_rejected(tmp_path: Path) -> None:
    """Chave desconhecida (typo) e YAML malformado são rejeitados."""
    shutil.copytree(CONFIGS_DIR, tmp_path / "cfg")
    finance = tmp_path / "cfg" / "finance.yaml"
    finance.write_text("finance:\n  custody_fee: 0.1\n", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        load_settings(tmp_path / "cfg")
    finance.write_text("finance: [\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="YAML inválido"):
        load_settings(tmp_path / "cfg")
    finance.write_text("- lista\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="mapeamento"):
        load_settings(tmp_path / "cfg")


def test_environment_overrides_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    """Variáveis TESOURO_* têm precedência sobre os YAML."""
    monkeypatch.setenv("TESOURO_FINANCE__CUSTODY_FEE_ANNUAL", "0.01")
    assert load_settings().finance.custody_fee_annual == 0.01

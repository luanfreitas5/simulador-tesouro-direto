"""Constantes sobre os títulos do Tesouro Direto e as colunas dos datasets."""

BOND_PREFIXED = "Tesouro Prefixado"
BOND_IPCA_PLUS = "Tesouro IPCA+"

# Apenas títulos "bullet" (sem cupons semestrais) são simulados: o fluxo de caixa
# é um único pagamento no vencimento.
SIMULATED_BONDS: tuple[str, ...] = (BOND_PREFIXED, BOND_IPCA_PLUS)

# Colunas originais do CSV do Tesouro Transparente -> nomes internos (inglês).
RAW_TESOURO_COLUMNS: dict[str, str] = {
    "Tipo Titulo": "bond_type",
    "Data Vencimento": "maturity_date",
    "Data Base": "reference_date",
    "Taxa Compra Manha": "buy_rate",
    "Taxa Venda Manha": "sell_rate",
    "PU Compra Manha": "buy_price",
    "PU Venda Manha": "sell_price",
    "PU Base Manha": "base_price",
}

TESOURO_DATE_FORMAT = "%d/%m/%Y"
SGS_DATE_FORMAT = "%d/%m/%Y"

GOLD_CURVE_COLUMNS: tuple[str, ...] = (
    "reference_date",
    "bond_type",
    "maturity_date",
    "years_to_maturity",
    "buy_rate",
    "sell_rate",
)

DAYS_PER_YEAR_CURVE = 365.25  # conversão de dias corridos para anos no eixo da curva

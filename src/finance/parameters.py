"""Parâmetros tributários e de convenção usados nos cálculos financeiros."""

from __future__ import annotations

from dataclasses import dataclass

from exceptions import InvalidInputError

# (limite superior inclusivo em dias corridos, alíquota sobre o rendimento).
# Valores de referência do IR regressivo — CONFIRA as regras vigentes.
DEFAULT_IR_BRACKETS: tuple[tuple[int, float], ...] = ((180, 0.225), (360, 0.20), (720, 0.175))


def _validate_rate(name: str, value: float, *, upper_exclusive: bool = False) -> None:
    upper_ok = value < 1 if upper_exclusive else value <= 1
    if not (value >= 0 and upper_ok):
        raise InvalidInputError(f"{name} deve estar entre 0 e 1; recebido: {value}")


def _validate_brackets(brackets: tuple[tuple[int, float], ...]) -> None:
    previous_limit = 0
    for max_days, rate in brackets:
        if max_days <= previous_limit:
            raise InvalidInputError(
                "Os limites das faixas do IR devem ser positivos e estritamente crescentes."
            )
        _validate_rate("Alíquota da faixa de IR", rate)
        previous_limit = max_days


@dataclass(frozen=True)
class TaxParams:
    """Alíquotas, taxas e convenções de prazo (todas configuráveis).

    Parameters
    ----------
    ir_brackets : tuple[tuple[int, float], ...]
        Faixas do IR regressivo ``(limite_em_dias_corridos_inclusivo, alíquota)``.
    ir_floor_rate : float
        Alíquota aplicada acima do último limite de ``ir_brackets``.
    custody_fee_annual : float
        Taxa de custódia anual (fração), rateada por dia corrido.
    business_days_per_year : int
        Dias úteis por ano na capitalização (convenção de mercado: 252).
    calendar_days_per_year : int
        Dias corridos por ano na anualização e no rateio da custódia.

    Raises
    ------
    InvalidInputError
        Se alguma alíquota/taxa estiver fora de [0, 1] ou as faixas forem inconsistentes.

    Examples
    --------
    >>> TaxParams(custody_fee_annual=0.0).custody_fee_annual
    0.0
    """

    ir_brackets: tuple[tuple[int, float], ...] = DEFAULT_IR_BRACKETS
    ir_floor_rate: float = 0.15
    custody_fee_annual: float = 0.002
    business_days_per_year: int = 252
    calendar_days_per_year: int = 365

    def __post_init__(self) -> None:
        """Valida os parâmetros na construção."""
        _validate_brackets(self.ir_brackets)
        _validate_rate("ir_floor_rate", self.ir_floor_rate)
        _validate_rate("custody_fee_annual", self.custody_fee_annual, upper_exclusive=True)
        if self.business_days_per_year <= 0 or self.calendar_days_per_year <= 0:
            raise InvalidInputError("Os dias por ano devem ser positivos.")


DEFAULT_TAX_PARAMS = TaxParams()

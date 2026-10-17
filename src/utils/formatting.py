"""Formatação de valores no padrão brasileiro."""


def format_brl(value: float) -> str:
    """Formata um valor em reais (``R$ 1.234,56``).

    Parameters
    ----------
    value : float
        Valor monetário.

    Returns
    -------
    str
        Texto formatado no padrão pt-BR.

    Examples
    --------
    >>> format_brl(1234.5)
    'R$ 1.234,50'
    """
    text = f"{abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sign = "-" if value < 0 and round(value, 2) != 0 else ""
    return f"{sign}R$ {text}"


def format_percent(value: float, decimals: int = 2) -> str:
    """Formata uma fração como porcentagem (``0.1234`` -> ``12,34%``).

    Parameters
    ----------
    value : float
        Valor em fração (0.10 = 10%).
    decimals : int, optional
        Casas decimais, by default 2.

    Returns
    -------
    str
        Texto formatado no padrão pt-BR.

    Examples
    --------
    >>> format_percent(0.1234)
    '12,34%'
    """
    return f"{value * 100:.{decimals}f}".replace(".", ",") + "%"

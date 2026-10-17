"""Exceções do módulo financeiro."""

from exceptions.base import TesouroError


class InvalidInputError(TesouroError, ValueError):
    """Entrada inválida para um cálculo financeiro (valor, prazo ou taxa)."""

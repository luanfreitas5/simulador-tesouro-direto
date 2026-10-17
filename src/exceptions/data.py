"""Exceções relacionadas a dados."""

from exceptions.base import TesouroError


class DataIngestionError(TesouroError):
    """Falha ao baixar ou ler dados de uma fonte externa."""


class DataValidationError(TesouroError):
    """Os dados violam o contrato (schema) esperado em uma camada."""


class DataNotFoundError(TesouroError):
    """Dado esperado (arquivo, cotação, vencimento) não foi encontrado."""

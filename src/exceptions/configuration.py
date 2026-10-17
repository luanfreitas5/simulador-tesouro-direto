"""Exceções relacionadas à configuração."""

from exceptions.base import TesouroError


class ConfigurationError(TesouroError):
    """Configuração ausente, malformada ou que viola o schema Pydantic."""

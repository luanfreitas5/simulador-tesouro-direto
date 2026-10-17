"""Exceções customizadas do projeto.

Hierarquia (todas herdam de ``TesouroError``):

- ``ConfigurationError``: configuração inválida ou ausente.
- ``DataIngestionError``: falha ao baixar/ler dados externos.
- ``DataValidationError``: dados violam o contrato (schema).
- ``DataNotFoundError``: dado esperado não encontrado.
- ``InvalidInputError``: entrada inválida (também é ``ValueError``).
"""

from exceptions.base import TesouroError
from exceptions.configuration import ConfigurationError
from exceptions.data import DataIngestionError, DataNotFoundError, DataValidationError
from exceptions.finance import InvalidInputError

__all__ = [
    "ConfigurationError",
    "DataIngestionError",
    "DataNotFoundError",
    "DataValidationError",
    "InvalidInputError",
    "TesouroError",
]

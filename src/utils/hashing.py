"""Funções de hash para rastrear a versão dos dados."""

import hashlib
from pathlib import Path


def hash_bytes(content: bytes) -> str:
    """Calcula o SHA-256 de um conteúdo em bytes.

    Parameters
    ----------
    content : bytes
        Conteúdo a ser resumido.

    Returns
    -------
    str
        Hash SHA-256 em hexadecimal.

    Examples
    --------
    >>> hash_bytes(b"")[:8]
    'e3b0c442'
    """
    return hashlib.sha256(content).hexdigest()


def hash_file(path: Path) -> str:
    """Calcula o SHA-256 de um arquivo, lendo-o em blocos.

    Parameters
    ----------
    path : Path
        Caminho do arquivo.

    Returns
    -------
    str
        Hash SHA-256 em hexadecimal.

    Raises
    ------
    FileNotFoundError
        Se o arquivo não existir.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

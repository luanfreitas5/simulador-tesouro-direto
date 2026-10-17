"""Download idempotente para a camada bronze, com cache local e snapshots imutáveis.

Layout: ``<bronze>/<fonte>/<AAAAMMDDTHHMMSSZ>/<arquivo>`` + ``manifest.json`` (URL,
SHA-256, tamanho e data do download). Um novo snapshot só é criado quando o conteúdo
muda; dentro do TTL nenhuma requisição é feita.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from exceptions import DataIngestionError, DataNotFoundError
from utils.hashing import hash_bytes

logger = logging.getLogger(__name__)

SNAPSHOT_FORMAT = "%Y%m%dT%H%M%SZ"
MANIFEST_FILE = "manifest.json"
LAST_CHECK_FILE = "last_checked.txt"

Fetcher = Callable[[str], bytes]


def http_get(url: str, timeout_seconds: int = 60, user_agent: str = "simulador-tesouro") -> bytes:
    """Baixa o conteúdo de uma URL via HTTP GET.

    Parameters
    ----------
    url : str
        Endereço a ser baixado.
    timeout_seconds : int, optional
        Tempo máximo de espera, by default 60.
    user_agent : str, optional
        Cabeçalho ``User-Agent``.

    Returns
    -------
    bytes
        Corpo da resposta.

    Raises
    ------
    DataIngestionError
        Se a requisição falhar ou retornar status de erro.
    """
    try:
        response = requests.get(url, timeout=timeout_seconds, headers={"User-Agent": user_agent})
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("Falha ao baixar %s", url)
        raise DataIngestionError(f"Falha ao baixar {url}: {exc}") from exc
    return response.content


def find_latest_snapshot(source_dir: Path) -> Path | None:
    """Retorna o snapshot mais recente de uma fonte, ou ``None`` se não houver.

    Parameters
    ----------
    source_dir : Path
        Diretório da fonte na camada bronze.

    Returns
    -------
    Path | None
        Diretório do snapshot mais recente.
    """
    if not source_dir.is_dir():
        return None
    snapshots = sorted(path for path in source_dir.iterdir() if path.is_dir())
    return snapshots[-1] if snapshots else None


def get_latest_file(source_dir: Path, filename: str) -> Path:
    """Retorna o caminho do arquivo no snapshot mais recente.

    Parameters
    ----------
    source_dir : Path
        Diretório da fonte na camada bronze.
    filename : str
        Nome do arquivo dentro do snapshot.

    Returns
    -------
    Path
        Caminho do arquivo.

    Raises
    ------
    DataNotFoundError
        Se não houver snapshot ou o arquivo não existir (rode a ingestão antes).
    """
    latest = find_latest_snapshot(source_dir)
    if latest is None or not (latest / filename).is_file():
        raise DataNotFoundError(
            f"Nenhum snapshot de '{filename}' em {source_dir}. Execute a ingestão primeiro."
        )
    return latest / filename


def _read_json(path: Path) -> dict[str, str]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _is_fresh(source_dir: Path, ttl_hours: float, now: datetime) -> bool:
    marker = source_dir / LAST_CHECK_FILE
    try:
        checked_at = datetime.fromisoformat(marker.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return now - checked_at < timedelta(hours=ttl_hours)


def _write_snapshot(
    source_dir: Path, filename: str, content: bytes, url: str, digest: str, now: datetime
) -> Path:
    snapshot_dir = source_dir / now.strftime(SNAPSHOT_FORMAT)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / filename).write_bytes(content)
    manifest = {
        "url": url,
        "filename": filename,
        "sha256": digest,
        "bytes": len(content),
        "downloaded_at": now.isoformat(),
    }
    (snapshot_dir / MANIFEST_FILE).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return snapshot_dir / filename


def ensure_snapshot(
    source_dir: Path,
    filename: str,
    fetch: Callable[[], bytes],
    url: str,
    ttl_hours: float = 24.0,
    force: bool = False,
    now: datetime | None = None,
) -> Path:
    """Garante um snapshot local do arquivo e retorna seu caminho (idempotente).

    - Dentro do TTL e sem ``force``: reutiliza o snapshot, sem rede.
    - Fora do TTL: baixa; se o SHA-256 for igual ao do último snapshot, reutiliza-o;
      caso contrário, grava um novo snapshot imutável.
    - Se o download falhar e houver snapshot anterior, usa-o (com aviso).

    Parameters
    ----------
    source_dir : Path
        Diretório da fonte na camada bronze.
    filename : str
        Nome do arquivo dentro do snapshot.
    fetch : Callable[[], bytes]
        Função sem argumentos que baixa o conteúdo.
    url : str
        URL de origem (registrada no manifest).
    ttl_hours : float, optional
        Validade do cache em horas, by default 24.
    force : bool, optional
        Ignora o cache e baixa novamente, by default False.
    now : datetime | None, optional
        Instante atual (injetável para testes); por padrão, UTC agora.

    Returns
    -------
    Path
        Caminho do arquivo no snapshot vigente.

    Raises
    ------
    DataIngestionError
        Se o download falhar e não houver snapshot anterior.

    Examples
    --------
    >>> ensure_snapshot(Path("data/bronze/x"), "a.csv", lambda: b"a", "http://x")  # doctest: +SKIP
    """
    now = now or datetime.now(timezone.utc)
    latest = find_latest_snapshot(source_dir)

    if latest is not None and not force and _is_fresh(source_dir, ttl_hours, now):
        logger.info("Cache válido para %s; nenhum download necessário.", source_dir.name)
        return latest / filename

    try:
        content = fetch()
    except DataIngestionError:
        if latest is None:
            raise
        logger.warning("Download falhou; usando o snapshot local de %s.", source_dir.name)
        return latest / filename

    digest = hash_bytes(content)
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / LAST_CHECK_FILE).write_text(now.isoformat(), encoding="utf-8")

    if latest is not None and _read_json(latest / MANIFEST_FILE).get("sha256") == digest:
        logger.info("Conteúdo de %s inalterado; snapshot mantido.", source_dir.name)
        return latest / filename

    path = _write_snapshot(source_dir, filename, content, url, digest, now)
    logger.info("Novo snapshot gravado: %s", path)
    return path

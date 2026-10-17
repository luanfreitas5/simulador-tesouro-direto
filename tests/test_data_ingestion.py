"""Testes da ingestão: cache idempotente, manifest, janelas do SGS e leitores."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path

import polars as pl
import pytest
import requests

from data.bcb import (
    build_sgs_url,
    fetch_sgs_series,
    sgs_filename,
    sgs_source_name,
    split_date_windows,
)
from data.downloader import ensure_snapshot, get_latest_file, http_get
from data.reader import read_parquet, read_sgs_json, read_tesouro_csv
from data.writer import write_parquet
from exceptions import DataIngestionError, DataNotFoundError
from utils.hashing import hash_bytes

T0 = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)


class Source:
    """Fonte simulada cujo conteúdo pode mudar entre chamadas."""

    def __init__(self, content: bytes = b"v1") -> None:
        self.content = content
        self.calls = 0

    def __call__(self) -> bytes:
        """Conta a chamada e devolve o conteúdo vigente."""
        self.calls += 1
        return self.content


def _snapshots(source_dir: Path) -> list[Path]:
    return sorted(p for p in source_dir.iterdir() if p.is_dir())


def test_first_call_downloads_and_writes_manifest(tmp_path: Path) -> None:
    """Primeira chamada baixa, grava o arquivo e o manifest com SHA-256."""
    source = Source()
    path = ensure_snapshot(tmp_path / "src", "a.csv", source, "http://x", now=T0)
    assert path.read_bytes() == b"v1"
    manifest = json.loads((path.parent / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sha256"] == hash_bytes(b"v1")
    assert manifest["url"] == "http://x"
    assert source.calls == 1


def test_within_ttl_uses_cache_without_network(tmp_path: Path) -> None:
    """Dentro do TTL, nenhuma requisição é feita (idempotência)."""
    source = Source()
    first = ensure_snapshot(tmp_path / "src", "a.csv", source, "http://x", now=T0)
    second = ensure_snapshot(
        tmp_path / "src", "a.csv", source, "http://x", now=T0 + timedelta(hours=1)
    )
    assert first == second
    assert source.calls == 1


def test_expired_ttl_same_content_keeps_single_snapshot(tmp_path: Path) -> None:
    """Fora do TTL, conteúdo idêntico não cria novo snapshot."""
    source = Source()
    first = ensure_snapshot(tmp_path / "src", "a.csv", source, "http://x", now=T0)
    again = ensure_snapshot(
        tmp_path / "src", "a.csv", source, "http://x", now=T0 + timedelta(hours=30)
    )
    assert source.calls == 2
    assert again == first
    assert len(_snapshots(tmp_path / "src")) == 1


def test_changed_content_creates_new_immutable_snapshot(tmp_path: Path) -> None:
    """Conteúdo novo gera outro snapshot; o anterior permanece intacto."""
    source = Source()
    first = ensure_snapshot(tmp_path / "src", "a.csv", source, "http://x", now=T0)
    source.content = b"v2"
    second = ensure_snapshot(
        tmp_path / "src", "a.csv", source, "http://x", now=T0 + timedelta(days=3)
    )
    assert second != first
    assert first.read_bytes() == b"v1"
    assert second.read_bytes() == b"v2"
    assert get_latest_file(tmp_path / "src", "a.csv") == second


def test_force_ignores_ttl(tmp_path: Path) -> None:
    """force=True baixa mesmo dentro do TTL."""
    source = Source()
    ensure_snapshot(tmp_path / "src", "a.csv", source, "http://x", now=T0)
    ensure_snapshot(
        tmp_path / "src", "a.csv", source, "http://x", force=True, now=T0 + timedelta(hours=1)
    )
    assert source.calls == 2


def test_download_failure_falls_back_to_local_snapshot(tmp_path: Path) -> None:
    """Com falha de rede, usa o snapshot existente; sem snapshot, propaga o erro."""
    good = Source()
    first = ensure_snapshot(tmp_path / "src", "a.csv", good, "http://x", now=T0)

    def failing() -> bytes:
        raise DataIngestionError("sem rede")

    fallback = ensure_snapshot(
        tmp_path / "src", "a.csv", failing, "http://x", now=T0 + timedelta(days=2)
    )
    assert fallback == first
    with pytest.raises(DataIngestionError):
        ensure_snapshot(tmp_path / "vazio", "a.csv", failing, "http://x", now=T0)


def test_get_latest_file_missing_raises(tmp_path: Path) -> None:
    """Sem snapshot, orienta a rodar a ingestão."""
    with pytest.raises(DataNotFoundError):
        get_latest_file(tmp_path / "nada", "a.csv")


def test_http_get_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """http_get devolve o corpo e converte erros de rede em DataIngestionError."""

    class Response:
        content = b"ok"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(requests, "get", lambda *a, **k: Response())
    assert http_get("http://x") == b"ok"

    def boom(*args: object, **kwargs: object) -> None:
        raise requests.ConnectionError("falhou")

    monkeypatch.setattr(requests, "get", boom)
    with pytest.raises(DataIngestionError):
        http_get("http://x")


def test_sgs_url_and_names() -> None:
    """A URL segue o formato da API de dados abertos do SGS."""
    url = build_sgs_url("http://x", 433, date(2020, 1, 1), date(2020, 12, 31))
    assert url == (
        "http://x/bcdata.sgs.433/dados?formato=json&dataInicial=01/01/2020&dataFinal=31/12/2020"
    )
    assert sgs_source_name(11) == "bcb_sgs_11"
    assert sgs_filename(11) == "serie_11.json"


def test_split_date_windows_are_contiguous_and_bounded() -> None:
    """Janelas cobrem o período sem lacunas, sobreposição ou excesso de anos."""
    windows = split_date_windows(date(2002, 1, 1), date(2024, 6, 30), 9)
    assert windows[0][0] == date(2002, 1, 1)
    assert windows[-1][1] == date(2024, 6, 30)
    assert len(windows) == 3
    for (_, previous_end), (next_start, _) in pairwise(windows):
        assert next_start == previous_end + timedelta(days=1)
    assert split_date_windows(date(2024, 2, 1), date(2024, 1, 1), 9) == []


def test_fetch_sgs_series_merges_windows_without_duplicates() -> None:
    """Registros repetidos entre janelas são deduplicados pela data."""
    urls: list[str] = []

    def fetch(url: str) -> bytes:
        urls.append(url)
        return json.dumps([{"data": "01/01/2024", "valor": "0.4"}]).encode()

    raw = fetch_sgs_series(433, date(2002, 1, 1), date(2024, 6, 30), "http://x", 9, fetch)
    merged = json.loads(raw)
    assert len(urls) == 3
    assert merged == [{"data": "01/01/2024", "valor": "0.4"}]


@pytest.mark.parametrize("payload", [b"nao-json", b'{"erro": "x"}'])
def test_fetch_sgs_series_rejects_bad_payload(payload: bytes) -> None:
    """Resposta que não é uma lista JSON é um erro de ingestão."""
    with pytest.raises(DataIngestionError):
        fetch_sgs_series(1, date(2024, 1, 1), date(2024, 1, 31), "http://x", 9, lambda _: payload)


def test_readers_and_writer_errors(tmp_path: Path) -> None:
    """Leitores sinalizam arquivo ausente ou conteúdo inválido."""
    with pytest.raises(DataNotFoundError):
        read_tesouro_csv(tmp_path / "x.csv")
    with pytest.raises(DataNotFoundError):
        read_sgs_json(tmp_path / "x.json")
    with pytest.raises(DataNotFoundError):
        read_parquet(tmp_path / "x.parquet")

    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(DataIngestionError):
        read_sgs_json(bad)
    bad.write_text('{"a": 1}', encoding="utf-8")
    with pytest.raises(DataIngestionError):
        read_sgs_json(bad)


def test_read_sgs_json_empty_and_parquet_roundtrip(tmp_path: Path) -> None:
    """Lista vazia vira DataFrame vazio com as colunas esperadas; parquet faz round-trip."""
    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    assert read_sgs_json(empty).columns == ["data", "valor"]

    df = pl.DataFrame({"a": [1, 2]})
    target = write_parquet(df, tmp_path / "sub" / "a.parquet")
    assert read_parquet(target).equals(df)

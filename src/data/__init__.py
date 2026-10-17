"""Ingestão e leitura/escrita de dados (camada bronze e I/O de parquet).

Módulos
-------
downloader
    ``ensure_snapshot``: download idempotente com cache local e manifest (SHA-256).
tesouro
    ``ingest_tesouro``: CSV de preços e taxas do Tesouro Transparente.
bcb
    ``ingest_sgs_series``: séries Selic e IPCA do SGS/BCB (janelas de até 10 anos).
reader
    Leitura dos arquivos brutos e de parquet.
writer
    ``write_parquet``.
"""

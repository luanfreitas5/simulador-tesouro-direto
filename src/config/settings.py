"""Configuração tipada do projeto, carregada de ``configs/*.yaml`` e validada com Pydantic."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from config.paths import CONFIGS_DIR, ROOT
from exceptions import ConfigurationError

# logging.yaml é dictConfig puro, aplicado por config.logging.configure_logging (não validado aqui).
CONFIG_FILES: tuple[str, ...] = ("config.yaml", "paths.yaml", "finance.yaml")

TESOURO_CSV_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
)


class StrictModel(BaseModel):
    """Base dos modelos de configuração: chaves desconhecidas (typos) são rejeitadas."""

    model_config = ConfigDict(extra="forbid")


class ProjectSettings(StrictModel):
    """Metadados do projeto."""

    name: str = "simulador-tesouro-direto"
    version: str = "0.1.0"
    random_seed: int = 42


class PathsSettings(StrictModel):
    """Diretórios das camadas de dados e saídas (relativos à raiz do projeto)."""

    bronze: Path = Path("data/bronze")
    silver: Path = Path("data/silver")
    gold: Path = Path("data/gold")
    reports: Path = Path("reports")
    logs: Path = Path("logs")

    def resolved(self, root: Path) -> PathsSettings:
        """Retorna uma cópia com todos os caminhos absolutos a partir de ``root``.

        Parameters
        ----------
        root : Path
            Diretório raiz usado para resolver caminhos relativos.

        Returns
        -------
        PathsSettings
            Configuração com caminhos absolutos (caminhos já absolutos são mantidos).
        """
        return PathsSettings(**{name: root / value for name, value in self})


class TesouroSource(StrictModel):
    """Fonte do CSV de preços e taxas do Tesouro Transparente."""

    url: str = TESOURO_CSV_URL
    filename: str = "PrecoTaxaTesouroDireto.csv"


class SgsSeries(StrictModel):
    """Códigos das séries do SGS/BCB utilizadas."""

    selic_daily: int = 11
    ipca_monthly: int = 433


class BcbSource(StrictModel):
    """Fonte das séries do SGS/BCB."""

    base_url: str = "https://api.bcb.gov.br/dados/serie"
    start_date: date = date(2002, 1, 1)
    max_window_years: int = Field(default=9, gt=0, le=10)
    series: SgsSeries = Field(default_factory=SgsSeries)


class IngestionSettings(StrictModel):
    """Parâmetros de ingestão (rede e cache local)."""

    cache_ttl_hours: float = Field(default=24.0, ge=0)
    timeout_seconds: int = Field(default=60, gt=0)
    user_agent: str = "simulador-tesouro-direto/0.1"
    tesouro: TesouroSource = Field(default_factory=TesouroSource)
    bcb: BcbSource = Field(default_factory=BcbSource)


class IrBracket(StrictModel):
    """Faixa do IR regressivo: até ``max_days`` dias corridos (inclusive) vale ``rate``."""

    max_days: int = Field(gt=0)
    rate: float = Field(ge=0, le=1)


def _default_brackets() -> list[IrBracket]:
    return [
        IrBracket(max_days=180, rate=0.225),
        IrBracket(max_days=360, rate=0.20),
        IrBracket(max_days=720, rate=0.175),
    ]


class FinanceSettings(StrictModel):
    """Parâmetros do módulo financeiro (alíquotas, taxas e premissas de projeção)."""

    ir_brackets: list[IrBracket] = Field(default_factory=_default_brackets)
    ir_floor_rate: float = Field(default=0.15, ge=0, le=1)
    custody_fee_annual: float = Field(default=0.002, ge=0, lt=1)
    business_days_per_year: int = Field(default=252, gt=0)
    projected_ipca_annual: float = Field(default=0.04, gt=-1, lt=1)
    projected_selic_annual: float = Field(default=0.10, gt=-1, lt=1)


class Settings(BaseSettings):
    """Configuração global do projeto.

    Os valores vêm dos YAML em ``configs/``; variáveis de ambiente com prefixo
    ``TESOURO_`` (aninhadas com ``__``, ex.: ``TESOURO_FINANCE__CUSTODY_FEE_ANNUAL``)
    têm precedência sobre o YAML. Chaves desconhecidas são rejeitadas para que erros
    de digitação falhem na inicialização.
    """

    model_config = SettingsConfigDict(
        extra="forbid", env_prefix="TESOURO_", env_nested_delimiter="__"
    )

    project: ProjectSettings = Field(default_factory=ProjectSettings)
    paths: PathsSettings = Field(default_factory=PathsSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    finance: FinanceSettings = Field(default_factory=FinanceSettings)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],  # noqa: ARG003
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Define a precedência: variáveis de ambiente sobrescrevem o YAML (init)."""
        return env_settings, init_settings


def read_yaml(path: Path) -> dict[str, Any]:
    """Lê um arquivo YAML e retorna seu conteúdo como dicionário.

    Parameters
    ----------
    path : Path
        Caminho do arquivo YAML.

    Returns
    -------
    dict[str, Any]
        Conteúdo do arquivo (vazio se o arquivo estiver vazio).

    Raises
    ------
    ConfigurationError
        Se o arquivo não existir, for YAML inválido ou não for um mapeamento.
    """
    if not path.is_file():
        raise ConfigurationError(f"Arquivo de configuração não encontrado: {path}")
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"YAML inválido em {path}: {exc}") from exc
    if content is None:
        return {}
    if not isinstance(content, dict):
        raise ConfigurationError(f"O arquivo {path} deve conter um mapeamento no topo.")
    return content


def load_settings(config_dir: Path = CONFIGS_DIR, root: Path = ROOT) -> Settings:
    """Carrega e valida as configurações a partir de ``config_dir``.

    Parameters
    ----------
    config_dir : Path, optional
        Diretório com os arquivos YAML, by default ``CONFIGS_DIR``.
    root : Path, optional
        Raiz usada para resolver os caminhos relativos, by default ``ROOT``.

    Returns
    -------
    Settings
        Configuração validada, com caminhos absolutos.

    Raises
    ------
    ConfigurationError
        Se algum arquivo estiver ausente/inválido ou violar o schema.

    Examples
    --------
    >>> settings = load_settings()
    >>> settings.finance.custody_fee_annual
    0.002
    """
    merged: dict[str, Any] = {}
    for filename in CONFIG_FILES:
        merged.update(read_yaml(config_dir / filename))
    try:
        settings = Settings(**merged)
    except ValidationError as exc:
        raise ConfigurationError(f"Configuração inválida:\n{exc}") from exc
    return settings.model_copy(update={"paths": settings.paths.resolved(root)})

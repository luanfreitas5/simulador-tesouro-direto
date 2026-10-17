"""Caminhos fixos do projeto, centralizados com ``pathlib.Path``."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIGS_DIR = ROOT / "configs"

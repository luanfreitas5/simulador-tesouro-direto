"""Gerenciamento de configuração do projeto.

Módulos
-------
paths
    Raiz do projeto e diretórios fixos (``ROOT``, ``CONFIGS_DIR``).
settings
    Modelos Pydantic e ``load_settings`` (YAML em ``configs/`` + variáveis de ambiente).
logging
    ``configure_logging``: handler Rich no console e arquivo com rotação diária.
"""

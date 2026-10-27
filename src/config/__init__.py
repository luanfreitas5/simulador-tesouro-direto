"""Gerenciamento de configuração do projeto.

Módulos
-------
paths
    Raiz do projeto e diretórios fixos (``ROOT``, ``CONFIGS_DIR``).
settings
    Modelos Pydantic e ``load_settings`` (YAML em ``configs/`` + variáveis de ambiente).
logging
    ``configure_logging`` (dictConfig a partir de ``configs/logging.yaml``), com handler Rich
    no console e arquivo ``logs/log_AAAA-MM-DD.log`` com rotação diária.
"""

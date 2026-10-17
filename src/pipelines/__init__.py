"""Orquestração dos fluxos de ponta a ponta.

Módulos
-------
ingestion
    ``run_ingestion``: bronze (download com cache e snapshots).
processing
    ``run_processing``: bronze -> silver -> gold, com contratos de dados.
plots
    ``run_plots``: gráficos HTML da curva de juros navegável por data.
simulation
    ``run_simulation``: simulação de uma compra a partir da curva e das séries macro.
"""

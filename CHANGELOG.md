# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e versionamento
[SemVer](https://semver.org/lang/pt-BR/).

## [Unreleased]

### Added

- Ingestão idempotente com cache local e snapshots imutáveis (Tesouro Transparente, Selic e IPCA do BCB SGS).
- Camadas silver e gold com contratos de dados (Pandera) e curva de juros por data.
- Módulo financeiro puro: IR regressivo, custódia, rentabilidade bruta, líquida e real.
- Gráfico da curva de juros navegável por data (Plotly) e app Streamlit com simulador.
- Testes unitários, de propriedades e de integração; CI, pre-commit e documentação.

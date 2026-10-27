# Atalhos reprodutíveis. `make check` replica o CI localmente.
# --- Configuração ----------------------------------------------------------
RUN := uv run python src/main.py    # 'src' vira raiz do path ao rodar o script

# PYTHONHASHSEED precisa ser exportado ANTES do interpretador iniciar: definido
# dentro do processo, não afeta a ordem de iteração de conjuntos já criada.
export PYTHONHASHSEED := 42

.DEFAULT_GOAL := help
.PHONY: help init venv install install-app update lock export \
	lint format typecheck security deadcode complexity docstrings modernize quality check \
	test smoke test-all coverage hooks pre-commit update-hooks release \
	docs docs-serve docs-deploy profile clean cache jupyter \
	ingest build plots pipeline app data train reproduce \
	clean-gold clean-silver clean-reports

help:  ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

init:  ## Inicializa o projeto (instala dependências + hooks)
	$(MAKE) install-app
	$(MAKE) hooks

venv:  ## Cria o ambiente virtual (requer: uv)
	uv venv

install:  ## Instala dependências (runtime + todos os grupos) e os hooks do pre-commit
	uv sync --locked --all-groups
	uv run pre-commit install --hook-type pre-commit --hook-type commit-msg

install-app:  ## Instala dependências + extra do aplicativo Streamlit
	uv sync --locked --all-groups --extra app

update:  ## Atualiza todas as dependências e sincroniza
	uv lock --upgrade
	uv sync --all-groups --extra app

lock:  ## Gera/atualiza o uv.lock
	uv lock

export:  ## Exporta requirements.txt (para quem usa pip)
	uv export --no-hashes -o requirements.txt

# --- Pipeline ---------------------------------------------------------------
ingest:  ## Bronze: baixa Tesouro Transparente + Selic/IPCA (BCB SGS), com cache local
	$(RUN) ingest

build:  ## Silver e gold: limpa, valida e constrói a curva de juros
	$(RUN) build

plots:  ## Gera o gráfico HTML da curva de juros navegável por data
	$(RUN) plots

pipeline:  ## Executa ingestão + processamento + gráficos
	$(RUN) all

data: ingest build  ## Alias: bronze -> silver -> gold (usado na seção "Reproduzir" do README)

train: pipeline  ## Alias: projeto sem treino de modelo; executa o pipeline completo

reproduce: pipeline  ## Reproduz os artefatos de ponta a ponta (sem DVC neste projeto)

app:  ## Sobe o simulador Streamlit (requer: make install-app e make pipeline)
	uv run --extra app streamlit run app/streamlit_app.py

# --- Qualidade -------------------------------------------------------------
lint:  ## Lint com ruff (somente verifica; espelha o CI)
	uv run ruff check .
	uv run ruff format --check .

format:  ## Formata e corrige com ruff
	uv run ruff check --fix .
	uv run ruff format .

typecheck:  ## Type checking estático (basedPyright)
	uv run basedpyright

security:  ## Análise de segurança (bandit + pip-audit)
	uv run bandit -r src -c pyproject.toml
	uv run pip-audit

deadcode:  ## Detecta código morto (vulture)
	uv run vulture src

complexity:  ## Limites de complexidade (xenon)
	uv run xenon --max-absolute B --max-modules A --max-average A src

docstrings:  ## Cobertura de docstrings (interrogate)
	uv run interrogate -v src

modernize:  ## Detecta código redundante (refurb)
	uv run refurb src

quality: lint typecheck security deadcode complexity docstrings modernize  ## Roda toda a suíte de qualidade (espelha o CI)

check: quality test  ## Roda tudo o que o CI roda (qualidade + testes com cobertura)

# --- Testes ----------------------------------------------------------------
test:  ## Roda os testes com cobertura
	uv run pytest -m "not slow"

smoke:  ## Roda apenas os smoke tests
	uv run pytest -m smoke -q --no-cov

test-all:  ## Roda a suíte completa, inclusive os testes lentos
	uv run pytest

coverage:  ## Gera o relatório de cobertura em HTML
	uv run pytest -m "not slow" --cov-report=html
	@echo "Relatório disponível em htmlcov/index.html"

hooks:  ## Instala os hooks do pre-commit e gera o baseline do detect-secrets
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg
	uv run detect-secrets scan > .secrets.baseline

pre-commit:  ## Roda todos os hooks do pre-commit em todos os arquivos
	uv run pre-commit run --all-files

update-hooks:  ## Atualiza os hooks do pre-commit
	uv run pre-commit autoupdate

release:  ## Cria uma nova release (versão + changelog + tag)
	uv run cz bump --changelog

# --- Limpeza (a camada bronze nunca é apagada) ------------------------------
clean-silver:  ## Remove a camada silver (derivada; reconstruível com make build)
	rm -f data/silver/*.parquet

clean-gold:  ## Remove a camada gold (derivada; reconstruível com make build)
	rm -f data/gold/*.parquet

clean-reports:  ## Remove os relatórios e figuras gerados
	rm -rf reports/figures/*

clean:  ## Remove caches e artefatos temporários
	rm -rf .pytest_cache .ruff_cache .hypothesis htmlcov coverage.xml site
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +

# --- Documentação ----------------------------------------------------------
docs:  ## Constrói a documentação (modo estrito)
	uv run mkdocs build --strict

docs-serve:  ## Servidor local da documentação
	uv run mkdocs serve

docs-deploy:  ## Publica a documentação no GitHub Pages
	uv run mkdocs gh-deploy --force

# --- Utilitários -----------------------------------------------------------
profile:  ## Profiling com scalene
	uv run scalene src/main.py

cache:  ## Limpa o cache do uv
	uv cache clean

jupyter:  ## Abre o JupyterLab
	uv run jupyter lab

.PHONY: help install sync run once test lint format typecheck clean docker docker-run precommit

PYTHON ?= python3.12
UV    ?= uv

help:  ## Show this help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install uv if missing.
	@command -v $(UV) >/dev/null 2>&1 || (echo "Installing uv..." && $(PYTHON) -m pip install --user uv)

sync:  ## Install project + dev dependencies into .venv.
	$(UV) sync --all-extras --dev

run:  ## Start the daily scheduler.
	$(UV) run news-aggregator

once:  ## Run the pipeline once and exit.
	$(UV) run news-aggregator --once

test:  ## Run the test suite.
	$(UV) run pytest tests/ -v

test-cov:  ## Run the test suite with coverage.
	$(UV) run pytest tests/ --cov=src/news_aggregator --cov-report=term-missing

lint:  ## Run ruff (lint).
	$(UV) run ruff check src/ tests/

lint-fix:  ## Run ruff (lint + autofix).
	$(UV) run ruff check --fix src/ tests/

format:  ## Run black + ruff format.
	$(UV) run black src/ tests/
	$(UV) run ruff format src/ tests/

format-check:  ## Verify formatting without changes.
	$(UV) run black --check src/ tests/
	$(UV) run ruff format --check src/ tests/

typecheck:  ## Run mypy.
	$(UV) run mypy src/news_aggregator

precommit:  ## Install pre-commit hooks.
	$(UV) run pre-commit install
	$(UV) run pre-commit run --all-files

docker:  ## Build the Docker image.
	docker build -t news-aggregator:latest .

docker-run:  ## Run the container with .env mounted.
	docker run --rm --env-file .env -v $(PWD)/config:/app/config:ro news-aggregator:latest --once

clean:  ## Remove caches and build artifacts.
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +

.PHONY: help install dev-install lint format test ingest eval seed serve docker-build docker-up docker-down clean

PYTHON ?= python
PIP ?= pip

help:
	@echo "RAGOps — Production RAG Platform Development Commands"
	@echo "----------------------------------------------------"
	@echo "make install      - Install production dependencies"
	@echo "make dev-install  - Install development and test dependencies"
	@echo "make lint         - Check code style with ruff"
	@echo "make format       - Format codebase with ruff"
	@echo "make test         - Run full test suite with coverage"
	@echo "make seed         - Initialize database and seed baseline records"
	@echo "make ingest       - Ingest documents from data/raw"
	@echo "make eval         - Run evaluation benchmark and quality gate"
	@echo "make serve        - Start the FastAPI server locally"
	@echo "make docker-build - Build production Docker images"
	@echo "make docker-up    - Launch full Docker Compose stack (API, Prometheus, Grafana, Jaeger)"
	@echo "make docker-down  - Stop Docker Compose stack"
	@echo "make clean        - Remove caches and temporary build artifacts"

install:
	$(PIP) install --upgrade pip hatchling
	$(PIP) install -e .

dev-install:
	$(PIP) install --upgrade pip hatchling
	$(PIP) install -e ".[dev]"

lint:
	ruff check src tests

format:
	ruff format src tests

test:
	pytest tests/ -v

seed:
	$(PYTHON) scripts/seed_database.py

ingest:
	$(PYTHON) scripts/ingest_documents.py --path data/raw --version v1

eval:
	$(PYTHON) scripts/run_evaluation.py --dataset evaluation/datasets/golden.jsonl --version v1 --fail-on-gate

serve:
	$(PYTHON) -m ragops.cli.main serve --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t ragops/api:latest -f docker/Dockerfile.api .
	docker build -t ragops/worker:latest -f docker/Dockerfile.worker .
	docker build -t ragops/evaluation:latest -f docker/Dockerfile.evaluation .

docker-up:
	docker compose -f compose/docker-compose.yml up -d

docker-down:
	docker compose -f compose/docker-compose.yml down

clean:
	rm -rf .pytest_cache build dist *.egg-info .coverage htmlcov

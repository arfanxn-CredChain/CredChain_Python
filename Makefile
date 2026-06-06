ENV_FILE ?= .env
ifneq (,$(wildcard $(ENV_FILE)))
    include $(ENV_FILE)
    export
endif

.PHONY: help install gen-fixtures serve dev test lint typecheck format \
	docker-up docker-up-build docker-down docker-logs docker-ps docker-fresh

help:
	@echo "CredChain Python - Available Commands:"
	@echo ""
	@echo "Local Development:"
	@echo "  make install         - Install deps with pip in editable mode (dev extras)"
	@echo "  make serve           - Run uvicorn (single worker)"
	@echo "  make dev             - Run uvicorn with --reload"
	@echo "  make test            - Run pytest"
	@echo "  make lint            - Run ruff check"
	@echo "  make typecheck       - Run mypy"
	@echo "  make format          - Run ruff format"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up       - docker compose up -d"
	@echo "  make docker-up-build - docker compose up -d --build"
	@echo "  make docker-down     - docker compose down"
	@echo "  make docker-logs     - tail compose logs"
	@echo "  make docker-ps       - list running containers"
	@echo "  make docker-fresh    - down + up-build + ps"

install:
	pip install -e ".[dev]"

gen-fixtures:
	.venv/bin/python tests/fixtures/gen_fixtures.py
	@echo ">>> Fixtures generated in tests/fixtures/"

serve:
	uvicorn app.main:app --host 0.0.0.0 --port 8081 --workers 1

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8081 --reload

test:
	pytest tests/ -v

lint:
	ruff check .

typecheck:
	mypy .

format:
	ruff format .

docker-up:
	docker compose up -d

docker-up-build:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-ps:
	docker compose ps

docker-fresh: docker-down docker-up-build docker-ps

ENV_FILE ?= .env
ifneq (,$(wildcard $(ENV_FILE)))
    include $(ENV_FILE)
    export
endif

.PHONY: help install download-models serve dev test lint typecheck format \
	docker-up docker-up-build docker-down docker-logs docker-ps docker-fresh

help:
	@echo "CredChain Python - Available Commands:"
	@echo ""
	@echo "Local Development:"
	@echo "  make install         - Install deps with pip in editable mode (dev extras)"
	@echo "  make download-models - Download EasyOCR + LaBSE + Qwen2.5-1.5B-Instruct to host"
	@echo "  make serve           - Run uvicorn (single worker)"
	@echo "  make dev             - Run uvicorn with --reload"
	@echo "  make test            - Run pytest"
	@echo "  make lint            - Run ruff check"
	@echo "  make typecheck       - Run mypy"
	@echo "  make format          - Run ruff format"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up       - docker compose up -d (requires download-models first)"
	@echo "  make docker-up-build - docker compose up -d --build"
	@echo "  make docker-down     - docker compose down"
	@echo "  make docker-logs     - tail compose logs"
	@echo "  make docker-ps       - list running containers"
	@echo "  make docker-fresh    - down + up-build + ps"

install:
	pip install -e ".[dev]"

download-models:
	@echo ">>> Downloading EasyOCR (id+en) into ./models/easyocr..."
	.venv/bin/python -c "import easyocr; easyocr.Reader(['id', 'en'], model_storage_directory='./models/easyocr', download_enabled=True)"
	@echo ">>> Downloading LaBSE into ./models/labse..."
	.venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/LaBSE').save('./models/labse')"
	@echo ">>> Downloading Qwen2.5-0.5B-Instruct-Q4_K_M.gguf into ./models/qwen..."
	.venv/bin/huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct-GGUF \
		--local-dir ./models/qwen \
		--include "qwen2.5-0.5b-instruct-q4_k_m.gguf"
	@echo ">>> All models downloaded."

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

.PHONY: install serve dev test lint typecheck format \
	docker-up docker-up-build docker-down docker-logs docker-ps docker-fresh

install:
	pip install -e ".[dev]"

serve:
	uvicorn app.main:app --host 0.0.0.0 --port 8081 --workers 1

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8081 --workers 1 --reload

test:
	pytest tests/ -v

lint:
	ruff check

typecheck:
	mypy app/ tests/

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

docker-fresh:
	docker compose down && docker compose up -d --build && docker compose ps

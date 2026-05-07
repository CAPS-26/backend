.PHONY: up down build logs migrate seed test lint format install shell

# Docker and build commands
up:
	docker compose up -d --remove-orphans

down:
	docker compose down --remove-orphans

build:
	docker compose build

logs:
	docker compose logs -f

# Development commands (local)
install:
	uv sync

migrate:
	uv run alembic upgrade head

seed:
	uv run python scripts/seed.py stations

test:
	uv run pytest -vv

lint:
	uv run ruff check . --fix
# uv run bandit -r . -c pyproject.toml

format:
	uv run ruff format .

shell:
	uv run python

# Run application locally
dev:
	uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

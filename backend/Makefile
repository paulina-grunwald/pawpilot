.PHONY: install dev lint format typecheck test check db-up db-down db-upgrade db-downgrade db-revision

install:
	uv sync

dev:
	uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy

test:
	TESTCONTAINERS_RYUK_DISABLED=true uv run pytest

check: lint typecheck test

db-up:
	docker compose -f ../infra/docker-compose.yml up -d

db-down:
	docker compose -f ../infra/docker-compose.yml down

db-upgrade:
	uv run alembic upgrade head

db-downgrade:
	uv run alembic downgrade -1

db-revision:
	uv run alembic revision --autogenerate -m "$(name)"

.PHONY: install dev lint format typecheck test check db-up db-down db-upgrade db-downgrade db-revision corpus-ingest retrieval-report rag-eval agent-eval guardrail-eval langsmith-experiments

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

# Ingest the vet corpus into Qdrant. Pass flags via ARGS, e.g.
# make corpus-ingest ARGS="--recreate"   /   make corpus-ingest ARGS="--limit 5"
corpus-ingest:
	uv run python -m scripts.corpus_ingest $(ARGS)

# Golden-set retrieval report (recall@k). Requires keys + an ingested corpus.
retrieval-report:
	uv run python -m scripts.retrieval_report $(ARGS)

# RAGAS dense-baseline eval. Installs the pinned RAGAS fork (evals group) first.
rag-eval:
	uv sync --group evals
	uv run python -m evals.rag.run_retrieval $(ARGS)

# Full RAGAS generation eval over the agent
agent-eval:
	uv sync --group evals
	uv run python -m evals.rag.run_agent_eval $(ARGS)

# Scope-guardrail eval: off-topic questions refused, dog questions answered.
# Needs live Gateway + Qdrant; no RAGAS judge, so no evals group required.
guardrail-eval:
	uv run python -m evals.rag.guardrail_eval $(ARGS)

# RAGAS evals as LangSmith Datasets + Experiments (opt-in; needs live LangSmith + Gateway creds)
langsmith-experiments:
	uv sync --group evals
	uv run python -m evals.rag.langsmith_experiment $(ARGS)

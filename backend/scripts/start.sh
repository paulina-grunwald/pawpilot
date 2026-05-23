#!/usr/bin/env sh
set -eu

# Run Alembic migrations against DATABASE_URL, then launch uvicorn.
# Fly.io sets PORT; default to 8000 for local docker runs.
PORT="${PORT:-8000}"

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn on 0.0.0.0:${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"

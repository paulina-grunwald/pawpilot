FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-default-groups

COPY . .
RUN uv sync --frozen --no-default-groups


FROM python:3.12-slim AS runtime

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 pawpilot

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MEDIA_ROOT=/app/media

WORKDIR /app
COPY --from=builder --chown=pawpilot:pawpilot /app /app

USER pawpilot
EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

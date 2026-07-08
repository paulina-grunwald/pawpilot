"""Tests for settings helpers — DB URL driver coercion for hosted Postgres."""

from __future__ import annotations

import pytest

from app.config import normalize_async_database_url


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        # Railway / Heroku-style bare schemes get the asyncpg driver.
        (
            "postgresql://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
        ),
        (
            "postgres://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
        ),
        # Already-qualified URLs are left untouched (idempotent).
        (
            "postgresql+asyncpg://user:pass@host:5432/db",
            "postgresql+asyncpg://user:pass@host:5432/db",
        ),
        # A different explicit driver is not rewritten.
        (
            "postgresql+psycopg2://user:pass@host:5432/db",
            "postgresql+psycopg2://user:pass@host:5432/db",
        ),
    ],
)
def test_normalize_async_database_url(raw_url: str, expected: str) -> None:
    assert normalize_async_database_url(raw_url) == expected


def test_normalize_preserves_query_and_credentials() -> None:
    raw_url = "postgres://u:p%40ss@host/db?sslmode=require"
    assert normalize_async_database_url(raw_url) == (
        "postgresql+asyncpg://u:p%40ss@host/db?sslmode=require"
    )

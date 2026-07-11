"""Tests for Postgres-backed agent persistence.

`to_psycopg_conninfo` is pure and covered exhaustively; `open_agent_persistence`
gets a real integration test against the session's test Postgres, proving the
advisory-locked table setup and that the returned store round-trips a fact.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock

import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.agent.memory import DogMemoryStore
from app.agent.persistence import (
    AgentPersistence,
    open_agent_persistence,
    to_psycopg_conninfo,
)
from tests.agent.conftest import make_agent_settings


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgresql+asyncpg://user:pw@host:5432/db", "postgresql://user:pw@host:5432/db"),
        ("postgresql+psycopg://user:pw@host/db", "postgresql://user:pw@host/db"),
        ("postgresql+psycopg2://user:pw@host/db", "postgresql://user:pw@host/db"),
        ("postgresql://user:pw@host/db", "postgresql://user:pw@host/db"),
        ("postgres://user:pw@host/db", "postgres://user:pw@host/db"),
    ],
)
def test_to_psycopg_conninfo_normalizes_driver(database_url: str, expected: str) -> None:
    assert to_psycopg_conninfo(database_url) == expected


async def test_agent_persistence_aclose_closes_pool() -> None:
    pool = AsyncMock(spec=AsyncConnectionPool)
    persistence = AgentPersistence(
        cast("AsyncConnectionPool[AsyncConnection[dict[str, object]]]", pool),
        cast(AsyncPostgresSaver, AsyncMock(spec=AsyncPostgresSaver)),
        cast(DogMemoryStore, AsyncMock(spec=DogMemoryStore)),
    )
    await persistence.aclose()
    pool.close.assert_awaited_once()


async def test_open_agent_persistence_round_trips_a_memory(database_url: str) -> None:
    settings = make_agent_settings()
    persistence = await open_agent_persistence(database_url, settings)
    try:
        assert isinstance(persistence.memory_store, DogMemoryStore)
        assert isinstance(persistence.checkpointer, AsyncPostgresSaver)

        await persistence.memory_store.asave("dog-persist", "breed", "Border Collie")
        facts = await persistence.memory_store.alist("dog-persist")
        assert [(fact.key, fact.value) for fact in facts] == [("breed", "Border Collie")]
    finally:
        await persistence.aclose()

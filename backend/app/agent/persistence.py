"""Postgres-backed persistence for the agent's short- and long-term memory.

`open_agent_persistence` opens one shared async connection pool and builds the
LangGraph `AsyncPostgresSaver` (thread checkpoints) and `AsyncPostgresStore`
(durable per-dog facts) over it, running their idempotent table setup. The
FastAPI lifespan owns the returned handle and closes the pool on shutdown.
"""

from __future__ import annotations

from typing import Any, cast

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.agent.config import AgentSettings
from app.agent.memory import DogMemoryStore

_CONNECTION_KWARGS: dict[str, Any] = {
    "autocommit": True,
    "prepare_threshold": 0,
    "row_factory": dict_row,
}
_SETUP_ADVISORY_LOCK_KEY = 0x70617770


def to_psycopg_conninfo(database_url: str) -> str:
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://", "postgresql+psycopg2://"):
        if database_url.startswith(prefix):
            return "postgresql://" + database_url[len(prefix) :]
    return database_url


class AgentPersistence:
    def __init__(
        self,
        pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]],
        checkpointer: AsyncPostgresSaver,
        memory_store: DogMemoryStore,
    ) -> None:
        self.pool = pool
        self.checkpointer = checkpointer
        self.memory_store = memory_store

    async def aclose(self) -> None:
        await self.pool.close()


async def open_agent_persistence(database_url: str, settings: AgentSettings) -> AgentPersistence:
    pool = cast(
        "AsyncConnectionPool[AsyncConnection[dict[str, Any]]]",
        AsyncConnectionPool(
            conninfo=to_psycopg_conninfo(database_url),
            min_size=1,
            max_size=settings.memory_pool_max_size,
            kwargs=_CONNECTION_KWARGS,
            open=False,
        ),
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    store = AsyncPostgresStore(pool)
    try:
        async with pool.connection() as connection:
            await connection.execute("SELECT pg_advisory_lock(%s)", (_SETUP_ADVISORY_LOCK_KEY,))
            try:
                await checkpointer.setup()
                await store.setup()
            finally:
                await connection.execute(
                    "SELECT pg_advisory_unlock(%s)", (_SETUP_ADVISORY_LOCK_KEY,)
                )
    except BaseException:
        await pool.close()
        raise
    memory_store = DogMemoryStore(store, max_memories=settings.max_dog_memories)
    return AgentPersistence(pool, checkpointer, memory_store)

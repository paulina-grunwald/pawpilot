"""Tests for the best-effort memory cleanup and thread-retention helpers.

`record_thread_quietly` and `clear_dog_memory_quietly` must never raise into the
request path, and `delete_stale_threads` must prune only cold threads while
delegating checkpoint deletion to the checkpointer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import cleanup as cleanup_module
from app.agent import runner
from app.agent.cleanup import (
    clear_dog_memory_quietly,
    delete_stale_threads,
    record_thread_quietly,
    run_thread_retention,
)
from app.agent.models import AgentThread
from tests.agent.conftest import build_test_agent


class _RecordingCheckpointer:
    """Records the thread ids it was asked to delete."""

    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def adelete_thread(self, thread_id: str) -> None:
        self.deleted.append(thread_id)


class _AsyncContextManager[ValueT]:
    """Wraps a value so it can stand in for an ``async with`` resource."""

    def __init__(self, value: ValueT) -> None:
        self._value = value

    async def __aenter__(self) -> ValueT:
        return self._value

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False


async def _all_thread_ids(session: AsyncSession) -> list[str]:
    rows = (await session.execute(select(AgentThread.thread_id))).scalars().all()
    return list(rows)


# --------------------------------------------------------------------------- #
# record_thread_quietly
# --------------------------------------------------------------------------- #


async def test_record_thread_inserts_row(db_session: AsyncSession) -> None:
    owner = uuid.uuid4()
    await record_thread_quietly(db_session, "thread-1", owner)

    rows = (await db_session.execute(select(AgentThread))).scalars().all()
    assert len(rows) == 1
    assert rows[0].thread_id == "thread-1"
    assert rows[0].owner_user_id == owner


async def test_record_thread_is_idempotent_and_keeps_owner(db_session: AsyncSession) -> None:
    first_owner = uuid.uuid4()
    second_owner = uuid.uuid4()
    await record_thread_quietly(db_session, "thread-1", first_owner)
    await record_thread_quietly(db_session, "thread-1", second_owner)

    rows = (await db_session.execute(select(AgentThread))).scalars().all()
    assert len(rows) == 1
    # ON CONFLICT only bumps updated_at; the original owner is preserved.
    assert rows[0].owner_user_id == first_owner


async def test_record_thread_swallows_errors() -> None:
    broken_session = AsyncMock(spec=AsyncSession)
    broken_session.execute.side_effect = RuntimeError("db down")

    # Must not raise despite the failing execute.
    await record_thread_quietly(cast(AsyncSession, broken_session), "thread-1", uuid.uuid4())

    broken_session.rollback.assert_awaited_once()


# --------------------------------------------------------------------------- #
# clear_dog_memory_quietly
# --------------------------------------------------------------------------- #


async def test_clear_dog_memory_removes_all_facts() -> None:
    agent = build_test_agent(responses=[AIMessage(content="hi")], with_memory=True)
    assert agent.memory_store is not None
    await agent.memory_store.asave("dog-1", "breed", "Aussie")
    runner.set_default_agent(agent)
    try:
        await clear_dog_memory_quietly("dog-1")
        assert await agent.memory_store.alist("dog-1") == []
    finally:
        runner.clear_default_agent()


async def test_clear_dog_memory_noop_without_default_agent() -> None:
    runner.clear_default_agent()
    # No default agent -> no store -> silent no-op, no error.
    await clear_dog_memory_quietly("dog-1")


async def test_clear_dog_memory_swallows_store_errors() -> None:
    agent = build_test_agent(responses=[AIMessage(content="hi")], with_memory=True)
    assert agent.memory_store is not None

    async def _boom(dog_id: str) -> None:
        raise RuntimeError("store exploded")

    agent.memory_store.aclear = _boom  # type: ignore[method-assign]
    runner.set_default_agent(agent)
    try:
        # The exception is logged, not raised.
        await clear_dog_memory_quietly("dog-1")
    finally:
        runner.clear_default_agent()


# --------------------------------------------------------------------------- #
# delete_stale_threads
# --------------------------------------------------------------------------- #


async def test_delete_stale_threads_prunes_only_cold_threads(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    db_session.add(
        AgentThread(
            thread_id="stale",
            owner_user_id=uuid.uuid4(),
            updated_at=now - timedelta(days=100),
        )
    )
    db_session.add(
        AgentThread(
            thread_id="fresh",
            owner_user_id=uuid.uuid4(),
            updated_at=now - timedelta(days=1),
        )
    )
    await db_session.commit()

    checkpointer = _RecordingCheckpointer()
    deleted = await delete_stale_threads(
        db_session, cast(AsyncPostgresSaver, checkpointer), timedelta(days=90)
    )

    assert deleted == 1
    assert checkpointer.deleted == ["stale"]
    assert await _all_thread_ids(db_session) == ["fresh"]


async def test_delete_stale_threads_noop_when_all_fresh(db_session: AsyncSession) -> None:
    db_session.add(
        AgentThread(
            thread_id="fresh",
            owner_user_id=uuid.uuid4(),
            updated_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    checkpointer = _RecordingCheckpointer()
    deleted = await delete_stale_threads(
        db_session, cast(AsyncPostgresSaver, checkpointer), timedelta(days=90)
    )

    assert deleted == 0
    assert checkpointer.deleted == []
    assert await _all_thread_ids(db_session) == ["fresh"]


# --------------------------------------------------------------------------- #
# run_thread_retention (orchestration)
# --------------------------------------------------------------------------- #


async def test_run_thread_retention_wires_checkpointer_and_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkpointer = _RecordingCheckpointer()
    session_sentinel = object()
    delete_mock = AsyncMock(return_value=4)

    monkeypatch.setattr(
        AsyncPostgresSaver,
        "from_conn_string",
        classmethod(lambda cls, conninfo: _AsyncContextManager(checkpointer)),
    )
    monkeypatch.setattr(
        cleanup_module, "session_factory", lambda: _AsyncContextManager(session_sentinel)
    )
    monkeypatch.setattr(cleanup_module, "delete_stale_threads", delete_mock)

    older_than = timedelta(days=30)
    result = await run_thread_retention(older_than)

    assert result == 4
    delete_mock.assert_awaited_once_with(session_sentinel, checkpointer, older_than)

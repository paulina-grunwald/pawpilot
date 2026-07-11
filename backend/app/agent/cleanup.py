"""Best-effort memory cleanup and thread retention.

`clear_dog_memory_quietly` drops a dog's durable facts when its pet is deleted;
`record_thread_quietly` tracks last activity per conversation so
`delete_stale_threads` can prune checkpoints that have gone cold. Recording and
clearing never raise into the request path — the worst case is a slightly stale
row, not a failed user-visible operation.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import runner
from app.agent.models import AgentThread
from app.agent.persistence import to_psycopg_conninfo
from app.config import settings
from app.db.base import session_factory

logger = logging.getLogger(__name__)


async def clear_dog_memory_quietly(dog_id: str) -> None:
    store = runner.active_memory_store()
    if store is None:
        return
    try:
        await store.aclear(dog_id)
    except Exception:
        logger.exception("best-effort dog memory clear failed for %s", dog_id)


async def record_thread_quietly(
    session: AsyncSession, thread_id: str, owner_user_id: uuid.UUID
) -> None:
    statement = (
        pg_insert(AgentThread)
        .values(thread_id=thread_id, owner_user_id=owner_user_id)
        .on_conflict_do_update(index_elements=["thread_id"], set_={"updated_at": func.now()})
    )
    try:
        await session.execute(statement)
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("best-effort agent thread record failed for %s", thread_id)


async def delete_stale_threads(
    session: AsyncSession, checkpointer: AsyncPostgresSaver, older_than: timedelta
) -> int:
    cutoff = datetime.now(UTC) - older_than
    result = await session.execute(
        select(AgentThread.thread_id).where(AgentThread.updated_at < cutoff)
    )
    stale_thread_ids = list(result.scalars().all())
    for thread_id in stale_thread_ids:
        await checkpointer.adelete_thread(thread_id)
    if stale_thread_ids:
        await session.execute(
            delete(AgentThread).where(AgentThread.thread_id.in_(stale_thread_ids))
        )
        await session.commit()
    return len(stale_thread_ids)


async def run_thread_retention(older_than: timedelta) -> int:
    conninfo = to_psycopg_conninfo(settings.database_url)
    async with (
        AsyncPostgresSaver.from_conn_string(conninfo) as checkpointer,
        session_factory() as session,
    ):
        return await delete_stale_threads(session, checkpointer, older_than)


if __name__ == "__main__":
    import asyncio
    import sys

    retention_days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    deleted = asyncio.run(run_thread_retention(timedelta(days=retention_days)))
    print(deleted)

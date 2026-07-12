"""``POST /agent/ask`` — the authenticated Ask PawPilot chat endpoint.

Maps the HTTP session to the agent's memory: the selected pet becomes the
long-term ``dog_id`` (owner-scoped) and ``thread_id`` continues a conversation.
The client-supplied thread id is namespaced by the user so one user can never
resume another user's conversation.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import runner
from app.agent.cleanup import record_thread_quietly
from app.agent.models import AgentThread
from app.agent.runner import PawPilotAgent, validate_query
from app.agent.schemas import (
    AgentAnswer,
    AgentAskRequest,
    AgentStreamError,
    AgentThreadDetail,
    AgentThreadSummary,
)
from app.auth.deps import current_active_user
from app.auth.models import User
from app.db.base import get_session
from app.pets.deps import load_owned_pet

logger = logging.getLogger(__name__)

_TITLE_MAX_LENGTH = 120

agent_router = APIRouter(prefix="/agent", tags=["agent"])


def get_agent() -> PawPilotAgent:
    return runner.get_default_agent()


def _thread_title(query: str) -> str:
    """A short, single-line title for a conversation, taken from its first question."""
    return " ".join(query.split())[:_TITLE_MAX_LENGTH]


@agent_router.post("/ask", response_model=AgentAnswer)
async def ask_pawpilot(
    payload: AgentAskRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    agent: PawPilotAgent = Depends(get_agent),
) -> AgentAnswer:
    dog_id: str | None = None
    if payload.pet_id is not None:
        pet = await load_owned_pet(payload.pet_id, user, session)
        dog_id = str(pet.id)
    thread_id = f"{user.id}:{payload.thread_id}" if payload.thread_id is not None else None
    try:
        answer = await agent.arun(payload.query, thread_id=thread_id, dog_id=dog_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except Exception as error:
        logger.exception("agent ask failed for user %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AGENT_UNAVAILABLE"
        ) from error
    if thread_id is not None:
        await record_thread_quietly(
            session, thread_id, user.id, pet_id=payload.pet_id, title=_thread_title(payload.query)
        )
    return answer


def _sse(event: BaseModel) -> str:
    return f"data: {event.model_dump_json()}\n\n"


@agent_router.post("/ask/stream")
async def ask_pawpilot_stream(
    payload: AgentAskRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    agent: PawPilotAgent = Depends(get_agent),
) -> StreamingResponse:
    try:
        validate_query(payload.query)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    dog_id: str | None = None
    if payload.pet_id is not None:
        pet = await load_owned_pet(payload.pet_id, user, session)
        dog_id = str(pet.id)
    thread_id = f"{user.id}:{payload.thread_id}" if payload.thread_id is not None else None

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for event in agent.astream_run(payload.query, thread_id=thread_id, dog_id=dog_id):
                yield _sse(event)
        except Exception:
            logger.exception("agent stream failed for user %s", user.id)
            yield _sse(AgentStreamError(detail="AGENT_UNAVAILABLE"))
            return
        if thread_id is not None:
            await record_thread_quietly(
                session,
                thread_id,
                user.id,
                pet_id=payload.pet_id,
                title=_thread_title(payload.query),
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@agent_router.get("/threads", response_model=list[AgentThreadSummary])
async def list_threads(
    pet_id: uuid.UUID | None = None,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
) -> list[AgentThreadSummary]:
    """List the current user's past conversations, newest first.

    Optionally filtered to a single dog. ``thread_id`` is returned in its
    client-facing form (the per-user namespace prefix stripped) so the frontend
    can resume the conversation by passing it back to ``/agent/ask``.
    """
    prefix = f"{user.id}:"
    statement = (
        select(AgentThread)
        .where(AgentThread.owner_user_id == user.id)
        .order_by(AgentThread.updated_at.desc())
    )
    if pet_id is not None:
        statement = statement.where(AgentThread.pet_id == pet_id)
    rows = (await session.execute(statement)).scalars().all()
    return [
        AgentThreadSummary(
            thread_id=row.thread_id.removeprefix(prefix),
            pet_id=row.pet_id,
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@agent_router.get("/threads/{thread_id}", response_model=AgentThreadDetail)
async def get_thread(
    thread_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_session),
    agent: PawPilotAgent = Depends(get_agent),
) -> AgentThreadDetail:
    """Return a past conversation's reconstructed transcript.

    Owner-scoped: the client id is re-namespaced with the user id before lookup,
    so a user can only read their own conversations.
    """
    namespaced_thread_id = f"{user.id}:{thread_id}"
    thread = await session.get(AgentThread, namespaced_thread_id)
    if thread is None or thread.owner_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="THREAD_NOT_FOUND")
    messages = await agent.aget_thread_transcript(namespaced_thread_id)
    return AgentThreadDetail(
        thread_id=thread_id,
        pet_id=thread.pet_id,
        title=thread.title,
        messages=messages,
    )

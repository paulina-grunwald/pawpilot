"""``POST /agent/ask`` — the authenticated Ask PawPilot chat endpoint.

Maps the HTTP session to the agent's memory: the selected pet becomes the
long-term ``dog_id`` (owner-scoped) and ``thread_id`` continues a conversation.
The client-supplied thread id is namespaced by the user so one user can never
resume another user's conversation.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import runner
from app.agent.cleanup import record_thread_quietly
from app.agent.runner import PawPilotAgent, validate_query
from app.agent.schemas import (
    AgentAnswer,
    AgentAskRequest,
    AgentStreamError,
)
from app.auth.deps import current_active_user
from app.auth.models import User
from app.db.base import get_session
from app.pets.deps import load_owned_pet

logger = logging.getLogger(__name__)

agent_router = APIRouter(prefix="/agent", tags=["agent"])


def get_agent() -> PawPilotAgent:
    return runner.get_default_agent()


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
        await record_thread_quietly(session, thread_id, user.id)
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
            await record_thread_quietly(session, thread_id, user.id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

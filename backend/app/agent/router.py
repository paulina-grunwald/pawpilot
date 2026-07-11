"""``POST /agent/ask`` — the authenticated Ask PawPilot chat endpoint.

Maps the HTTP session to the agent's memory: the selected pet becomes the
long-term ``dog_id`` (owner-scoped) and ``thread_id`` continues a conversation.
The client-supplied thread id is namespaced by the user so one user can never
resume another user's conversation.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import runner
from app.agent.runner import PawPilotAgent
from app.agent.schemas import AgentAnswer, AgentAskRequest
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
        return await agent.arun(payload.query, thread_id=thread_id, dog_id=dog_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    except Exception as error:
        logger.exception("agent ask failed for user %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AGENT_UNAVAILABLE"
        ) from error

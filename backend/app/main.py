"""FastAPI app entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent import runner
from app.agent.config import get_agent_settings
from app.agent.persistence import AgentPersistence, open_agent_persistence
from app.agent.router import agent_router
from app.auth.router import auth_router, users_router
from app.config import settings
from app.integrations.tractive.router import tractive_router
from app.journal.router import journal_router
from app.pets.breeds_router import breeds_router
from app.pets.router import pets_router
from app.rag.admin_router import admin_rag_router
from app.rag.observability import configure_langsmith
from app.rag.router import rag_router

# Set LangSmith EU endpoint + project defaults before any client is built.
configure_langsmith()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    persistence: AgentPersistence | None = None
    agent_settings = get_agent_settings()
    if agent_settings.memory_backend == "postgres":
        persistence = await open_agent_persistence(settings.database_url, agent_settings)
        runner.set_default_agent(
            runner.build_agent(
                checkpointer=persistence.checkpointer,
                memory_store=persistence.memory_store,
            )
        )
    try:
        yield
    finally:
        if persistence is not None:
            runner.clear_default_agent()
            await persistence.aclose()


app = FastAPI(title="PawPilot", version="0.0.0", lifespan=lifespan)

# Pet photos are NOT served from a public static mount — they are streamed by
# the authenticated, owner-scoped GET /pets/{id}/photo route so a photo is only
# reachable by its owner. MediaStorage creates upload directories lazily on save.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(pets_router)
app.include_router(journal_router)
app.include_router(breeds_router)
app.include_router(tractive_router)
app.include_router(rag_router)
app.include_router(admin_rag_router)
app.include_router(agent_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

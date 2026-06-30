"""FastAPI app entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import auth_router, users_router
from app.config import settings
from app.integrations.tractive.router import tractive_router
from app.pets.breeds_router import breeds_router
from app.pets.router import pets_router
from app.rag.observability import configure_langsmith
from app.rag.router import rag_router

# Set LangSmith EU endpoint + project defaults before any client is built.
configure_langsmith()

app = FastAPI(title="PawPilot", version="0.0.0")

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
app.include_router(breeds_router)
app.include_router(tractive_router)
app.include_router(rag_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

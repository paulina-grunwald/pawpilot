"""FastAPI app entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.router import auth_router, users_router
from app.config import settings
from app.integrations.tractive.router import tractive_router
from app.media.deps import get_media_root
from app.pets.breeds_router import breeds_router
from app.pets.router import pets_router

app = FastAPI(title="PawPilot", version="0.0.0")

_media_root = get_media_root()
_media_root.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=_media_root), name="media")

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

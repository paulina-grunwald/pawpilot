"""Admin corpus loading: ``POST /admin/rag/{collection,upsert}``.

Loads the vet corpus into the *private* deployed Qdrant without exposing Qdrant
publicly: an operator embeds the corpus locally and posts the resulting points
here, and the backend upserts them over its private network. Gated by a shared
admin token so it is not an open write endpoint.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient, models

from app.config import settings
from app.rag.config import RagSettings, get_rag_settings
from app.rag.store import DENSE_VECTOR, ensure_collection, upsert_points


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    expected = settings.admin_ingest_token
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ADMIN_INGEST_DISABLED"
        )
    if x_admin_token is None or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ADMIN_TOKEN_INVALID")


def get_admin_rag_settings() -> RagSettings:
    return get_rag_settings()


def get_admin_qdrant_client(
    rag_settings: RagSettings = Depends(get_admin_rag_settings),
) -> QdrantClient:
    return QdrantClient(url=rag_settings.qdrant_url, api_key=rag_settings.qdrant_api_key)


class CollectionRequest(BaseModel):
    vector_size: int = Field(ge=1)
    recreate: bool = False


class CollectionResponse(BaseModel):
    collection: str
    vector_size: int
    recreated: bool


class UpsertPoint(BaseModel):
    id: str = Field(min_length=1)
    vector: list[float] = Field(min_length=1)
    payload: dict[str, object]


class SourceUpsertRequest(BaseModel):
    source_id: str = Field(min_length=1)
    points: list[UpsertPoint] = Field(min_length=1)


class UpsertResponse(BaseModel):
    source_id: str
    upserted: int


admin_rag_router = APIRouter(
    prefix="/admin/rag",
    tags=["admin-rag"],
    dependencies=[Depends(require_admin_token)],
)


@admin_rag_router.post("/collection", response_model=CollectionResponse)
async def prepare_collection(
    request: CollectionRequest,
    rag_settings: RagSettings = Depends(get_admin_rag_settings),
    client: QdrantClient = Depends(get_admin_qdrant_client),
) -> CollectionResponse:
    await run_in_threadpool(
        ensure_collection,
        client,
        rag_settings.collection,
        request.vector_size,
        recreate=request.recreate,
    )
    return CollectionResponse(
        collection=rag_settings.collection,
        vector_size=request.vector_size,
        recreated=request.recreate,
    )


@admin_rag_router.post("/upsert", response_model=UpsertResponse)
async def upsert_source(
    request: SourceUpsertRequest,
    rag_settings: RagSettings = Depends(get_admin_rag_settings),
    client: QdrantClient = Depends(get_admin_qdrant_client),
) -> UpsertResponse:
    points = [
        models.PointStruct(id=point.id, vector={DENSE_VECTOR: point.vector}, payload=point.payload)
        for point in request.points
    ]
    upserted = await run_in_threadpool(
        upsert_points, client, rag_settings.collection, request.source_id, points
    )
    return UpsertResponse(source_id=request.source_id, upserted=upserted)

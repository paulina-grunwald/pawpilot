from __future__ import annotations

from collections.abc import Iterator

import pytest
from httpx import AsyncClient
from qdrant_client import QdrantClient

from app.config import settings as app_settings
from app.main import app
from app.rag.admin_router import get_admin_qdrant_client, get_admin_rag_settings
from app.rag.config import RagSettings
from app.rag.store import chunk_point_id

pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect")

_TOKEN = "test-admin-token"
_HEADERS = {"X-Admin-Token": _TOKEN}
_COLLECTION = "admin_router_test"
_DIM = 16


@pytest.fixture
def qdrant() -> QdrantClient:
    return QdrantClient(":memory:")


@pytest.fixture
def admin_env(qdrant: QdrantClient, monkeypatch: pytest.MonkeyPatch) -> Iterator[QdrantClient]:
    fake_settings = RagSettings(
        gateway_api_key="test-key", collection=_COLLECTION, embed_dimensions=_DIM
    )
    monkeypatch.setattr(app_settings, "admin_ingest_token", _TOKEN)
    app.dependency_overrides[get_admin_rag_settings] = lambda: fake_settings
    app.dependency_overrides[get_admin_qdrant_client] = lambda: qdrant
    try:
        yield qdrant
    finally:
        app.dependency_overrides.pop(get_admin_rag_settings, None)
        app.dependency_overrides.pop(get_admin_qdrant_client, None)


def _point(source_id: str, index: int) -> dict[str, object]:
    text = f"{source_id}-chunk-{index}"
    return {
        "id": chunk_point_id(source_id, index, text),
        "vector": [float(index + 1) / _DIM] * _DIM,
        "payload": {"source_id": source_id, "chunk_id": f"{source_id}:{index}", "text": text},
    }


async def _create_collection(client: AsyncClient) -> None:
    response = await client.post(
        "/admin/rag/collection", json={"vector_size": _DIM, "recreate": True}, headers=_HEADERS
    )
    assert response.status_code == 200, response.text


async def test_missing_token_returns_401(client: AsyncClient, admin_env: QdrantClient) -> None:
    response = await client.post("/admin/rag/collection", json={"vector_size": _DIM})
    assert response.status_code == 401
    assert response.json()["detail"] == "ADMIN_TOKEN_INVALID"


async def test_wrong_token_returns_401(client: AsyncClient, admin_env: QdrantClient) -> None:
    response = await client.post(
        "/admin/rag/collection", json={"vector_size": _DIM}, headers={"X-Admin-Token": "nope"}
    )
    assert response.status_code == 401


async def test_disabled_returns_503(
    client: AsyncClient, admin_env: QdrantClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_settings, "admin_ingest_token", None)
    response = await client.post(
        "/admin/rag/collection", json={"vector_size": _DIM}, headers=_HEADERS
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "ADMIN_INGEST_DISABLED"


async def test_prepare_collection_creates(client: AsyncClient, admin_env: QdrantClient) -> None:
    response = await client.post(
        "/admin/rag/collection", json={"vector_size": _DIM, "recreate": True}, headers=_HEADERS
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"collection": _COLLECTION, "vector_size": _DIM, "recreated": True}
    assert admin_env.collection_exists(_COLLECTION)


async def test_upsert_source_upserts_points(client: AsyncClient, admin_env: QdrantClient) -> None:
    await _create_collection(client)
    points = [_point("s1", index) for index in range(3)]
    response = await client.post(
        "/admin/rag/upsert", json={"source_id": "s1", "points": points}, headers=_HEADERS
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"source_id": "s1", "upserted": 3}
    assert admin_env.count(_COLLECTION).count == 3


async def test_upsert_prunes_stale_chunks(client: AsyncClient, admin_env: QdrantClient) -> None:
    await _create_collection(client)
    await client.post(
        "/admin/rag/upsert",
        json={"source_id": "s1", "points": [_point("s1", index) for index in range(4)]},
        headers=_HEADERS,
    )
    await client.post(
        "/admin/rag/upsert",
        json={"source_id": "s1", "points": [_point("s1", index) for index in range(2)]},
        headers=_HEADERS,
    )
    # Re-upserting the source with fewer chunks prunes the ones that vanished.
    assert admin_env.count(_COLLECTION).count == 2


async def test_upsert_rejects_empty_points(client: AsyncClient, admin_env: QdrantClient) -> None:
    response = await client.post(
        "/admin/rag/upsert", json={"source_id": "s1", "points": []}, headers=_HEADERS
    )
    assert response.status_code == 422

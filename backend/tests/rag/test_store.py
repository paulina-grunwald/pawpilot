from __future__ import annotations

import pytest
from qdrant_client import QdrantClient

from app.rag.store import chunk_point_id, ensure_collection

pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect")

_COLLECTION = "store_test"


def test_ensure_collection_creates_and_is_idempotent() -> None:
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, 16)
    assert client.collection_exists(_COLLECTION)

    ensure_collection(client, _COLLECTION, 16)
    assert client.collection_exists(_COLLECTION)


def test_ensure_collection_recreate_rebuilds() -> None:
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, 16)
    ensure_collection(client, _COLLECTION, 16, recreate=True)
    assert client.count(_COLLECTION).count == 0


def test_ensure_collection_rejects_dimension_mismatch() -> None:
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, 16)
    with pytest.raises(ValueError, match="dense vector size 16"):
        ensure_collection(client, _COLLECTION, 32)


def test_ensure_collection_recreate_accepts_new_dimensions() -> None:
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, 16)
    # --recreate is the escape hatch for a changed embedding dimension.
    ensure_collection(client, _COLLECTION, 32, recreate=True)
    assert client.collection_exists(_COLLECTION)


def test_chunk_point_id_is_stable_and_content_addressed() -> None:
    first = chunk_point_id("src", 0, "hello")
    assert first == chunk_point_id("src", 0, "hello")
    assert first != chunk_point_id("src", 0, "world")
    assert first != chunk_point_id("src", 1, "hello")

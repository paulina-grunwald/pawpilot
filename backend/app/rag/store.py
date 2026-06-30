"""Qdrant collection schema + point-id helpers shared by ingest and retrieval.

The ``vet_corpus`` collection uses a named ``dense`` vector (cosine). Chunk point
ids are a UUIDv5 of ``(source_id, chunk_index, sha256(text)[:16])`` so re-running
ingest upserts in place (idempotent), and a changed chunk replaces its own point.
"""

from __future__ import annotations

import hashlib
import uuid

from qdrant_client import QdrantClient, models

DENSE_VECTOR = "dense"
_INDEXED_PAYLOAD_FIELDS = ("source_id", "source_tier")


def ensure_collection(
    client: QdrantClient,
    collection: str,
    vector_size: int,
    *,
    recreate: bool = False,
) -> None:
    """Create the collection (+ payload indexes) if absent; optionally rebuild."""
    if recreate and client.collection_exists(collection):
        client.delete_collection(collection)
    if client.collection_exists(collection):
        return
    client.create_collection(
        collection_name=collection,
        vectors_config={
            DENSE_VECTOR: models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        },
    )
    for field_name in _INDEXED_PAYLOAD_FIELDS:
        client.create_payload_index(
            collection_name=collection,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


def chunk_point_id(source_id: str, chunk_index: int, text: str) -> str:
    """Stable UUIDv5 point id for an idempotent upsert."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{chunk_index}:{digest}"))

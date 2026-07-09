"""Qdrant collection schema + point-id helpers shared by ingest and retrieval."""

from __future__ import annotations

import hashlib
import uuid

from qdrant_client import QdrantClient, models

DENSE_VECTOR = "dense"
_INDEXED_PAYLOAD_FIELDS = ("source_id", "source_tier")


def _dense_vector_size(client: QdrantClient, collection: str) -> int:
    vectors = client.get_collection(collection).config.params.vectors
    params = vectors[DENSE_VECTOR] if isinstance(vectors, dict) else vectors
    if params is None:
        raise ValueError(f"collection {collection!r} has no dense vector configuration")
    return params.size


def ensure_collection(
    client: QdrantClient,
    collection: str,
    vector_size: int,
    *,
    recreate: bool = False,
) -> None:
    """Create the collection (+ payload indexes) if absent; optionally rebuild.

    When the collection already exists, its dense-vector size must match
    ``vector_size``; a mismatch (embedding model / dimensions changed) raises so
    the caller rebuilds with ``recreate=True`` instead of silently corrupting the
    index one failed upsert at a time.
    """
    if recreate and client.collection_exists(collection):
        client.delete_collection(collection)
    if client.collection_exists(collection):
        existing_size = _dense_vector_size(client, collection)
        if existing_size != vector_size:
            raise ValueError(
                f"collection {collection!r} has dense vector size {existing_size}, but the "
                f"configuration expects {vector_size}; re-run ingest with --recreate to rebuild."
            )
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


def _delete_stale_chunks(
    client: QdrantClient, collection: str, source_id: str, keep_ids: list[str]
) -> None:
    """Delete the source's points except the ones we just upserted (the stale set)."""
    client.delete(
        collection_name=collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(key="source_id", match=models.MatchValue(value=source_id))
                ],
                must_not=[models.HasIdCondition(has_id=list(keep_ids))],
            )
        ),
    )


def upsert_points(
    client: QdrantClient,
    collection: str,
    source_id: str,
    points: list[models.PointStruct],
) -> int:
    """Upsert a source's points, then prune that source's now-stale chunks.

    The Qdrant-write half of ingest — no PDF/embedding deps — shared by the local
    ingest path and the admin upsert endpoint (which receives points embedded
    elsewhere), so the serving image never imports the pypdf-based ingest module.
    """
    client.upsert(collection_name=collection, points=points)
    _delete_stale_chunks(client, collection, source_id, [str(point.id) for point in points])
    return len(points)

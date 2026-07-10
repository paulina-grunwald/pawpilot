"""Corpus ingest: PDF -> chunks -> embeddings -> idempotent Qdrant upsert.

Importable so the pure parts (payload + point construction) are unit-tested; the
CLI lives in ``scripts/corpus_ingest.py``. Idempotency comes from the UUIDv5
point ids (`store.chunk_point_id`) plus a per-source upsert-then-delete-stale, so
a changed document replaces only its own chunks without a window where the source
is missing from the collection.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pypdf import PdfReader
from qdrant_client import QdrantClient, models

from app.rag.chunking import ChunkRecord, PageText, chunk_pages
from app.rag.embeddings import Embedder
from app.rag.manifest import CorpusSource, resolve_source_tier
from app.rag.schemas import SourceTier
from app.rag.store import DENSE_VECTOR, chunk_point_id, upsert_points

_logger = logging.getLogger(__name__)


def read_pdf_pages(path: Path) -> list[PageText]:
    """Extract per-page text from a PDF (page numbers are 1-based)."""
    reader = PdfReader(str(path))
    return [
        PageText(page_number=index, text=page.extract_text() or "")
        for index, page in enumerate(reader.pages, start=1)
    ]


def _citation_payload(source: CorpusSource, tier: SourceTier) -> dict[str, object]:
    return {
        "source_id": source.source_id,
        "title": source.title,
        "organization": source.organization,
        "year": source.year if source.year is not None else "n.d.",
        "url": source.url,
        "source_tier": tier,
        "license_note": source.license_note,
    }


def build_points(
    source: CorpusSource,
    tier: SourceTier,
    records: list[ChunkRecord],
    vectors: list[list[float]],
) -> list[models.PointStruct]:
    """Build Qdrant points (citation payload + dense vector) for a source's chunks."""
    citation = _citation_payload(source, tier)
    points: list[models.PointStruct] = []
    for record, vector in zip(records, vectors, strict=True):
        payload: dict[str, object] = {
            **citation,
            "chunk_id": f"{source.source_id}:{record.chunk_index}",
            "text": record.text,
            "section": record.section,
            "page_start": record.page_start,
            "page_end": record.page_end,
        }
        points.append(
            models.PointStruct(
                id=chunk_point_id(source.source_id, record.chunk_index, record.text),
                vector={DENSE_VECTOR: vector},
                payload=payload,
            )
        )
    return points


def ingest_source(
    client: QdrantClient,
    embedder: Embedder,
    collection: str,
    source: CorpusSource,
    raw_dir: Path,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> int:
    """Ingest one source; returns the number of chunks upserted (0 if no text)."""
    pages = read_pdf_pages(raw_dir / source.file)
    records = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not records:
        _logger.warning(
            "source %r produced no chunks; leaving any existing chunks in place",
            source.source_id,
        )
        return 0
    vectors = embedder.embed_documents([record.text for record in records])
    points = build_points(source, resolve_source_tier(source), records, vectors)
    return upsert_points(client, collection, source.source_id, points)

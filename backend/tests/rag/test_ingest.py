from __future__ import annotations

from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from app.rag.chunking import ChunkRecord, PageText
from app.rag.fakes import FakeEmbedder
from app.rag.ingest import build_points, ingest_source
from app.rag.manifest import CorpusSource
from app.rag.store import ensure_collection

pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect")

_COLLECTION = "ingest_test"
_DIM = 16


def _source(
    source_id: str = "wsava-vaccination-2024", year: int | str | None = 2024
) -> CorpusSource:
    return CorpusSource(
        source_id=source_id,
        title="Vaccination Guidelines",
        organization="WSAVA",
        year=year,
        url="https://example.org/a.pdf",
        file="a.pdf",
        license_note="free guideline",
    )


def _records() -> list[ChunkRecord]:
    return [
        ChunkRecord(
            text="core vaccines",
            page_start=1,
            page_end=1,
            section="Core",
            start_index=0,
            chunk_index=0,
        ),
        ChunkRecord(
            text="booster timing",
            page_start=2,
            page_end=2,
            section="Boosters",
            start_index=0,
            chunk_index=1,
        ),
    ]


def test_build_points_payload_and_chunk_id() -> None:
    embedder = FakeEmbedder(_DIM)
    records = _records()
    vectors = embedder.embed_documents([record.text for record in records])
    points = build_points(_source(), "guideline", records, vectors)

    assert len(points) == 2
    payload = points[0].payload
    assert payload is not None
    assert payload["source_id"] == "wsava-vaccination-2024"
    assert payload["source_tier"] == "guideline"
    assert payload["chunk_id"] == "wsava-vaccination-2024:0"
    assert payload["page_start"] == 1
    assert payload["text"] == "core vaccines"


def test_build_points_ids_are_idempotent() -> None:
    embedder = FakeEmbedder(_DIM)
    records = _records()
    vectors = embedder.embed_documents([record.text for record in records])
    first = build_points(_source(), "guideline", records, vectors)
    second = build_points(_source(), "guideline", records, vectors)
    assert [point.id for point in first] == [point.id for point in second]


def test_build_points_maps_missing_year_to_label() -> None:
    embedder = FakeEmbedder(_DIM)
    records = _records()
    vectors = embedder.embed_documents([record.text for record in records])
    points = build_points(_source(year=None), "primary_research", records, vectors)
    payload = points[0].payload
    assert payload is not None
    assert payload["year"] == "n.d."


def test_ingest_source_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = [
        PageText(page_number=1, text="core vaccines protect dogs from disease"),
        PageText(page_number=2, text="boosters are given annually for adult dogs"),
    ]
    monkeypatch.setattr("app.rag.ingest.read_pdf_pages", lambda path: pages)
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, _DIM, recreate=True)
    embedder = FakeEmbedder(_DIM)

    first = ingest_source(client, embedder, _COLLECTION, _source(), Path("/tmp"))
    count_after_first = client.count(_COLLECTION).count
    second = ingest_source(client, embedder, _COLLECTION, _source(), Path("/tmp"))
    count_after_second = client.count(_COLLECTION).count

    assert first == second > 0
    # Re-ingesting the same source replaces its chunks in place — no duplicates.
    assert count_after_first == count_after_second


def test_ingest_source_keeps_existing_chunks_when_embedding_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = [
        PageText(page_number=1, text="core vaccines protect dogs from disease"),
        PageText(page_number=2, text="boosters are given annually for adult dogs"),
    ]
    monkeypatch.setattr("app.rag.ingest.read_pdf_pages", lambda path: pages)
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, _DIM, recreate=True)

    ingest_source(client, FakeEmbedder(_DIM), _COLLECTION, _source(), Path("/tmp"))
    count_before = client.count(_COLLECTION).count
    assert count_before > 0

    class _FailingEmbedder(FakeEmbedder):
        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("transient embedding failure")

    with pytest.raises(RuntimeError, match="transient embedding failure"):
        ingest_source(client, _FailingEmbedder(_DIM), _COLLECTION, _source(), Path("/tmp"))

    # Embedding fails before the upsert, so no stale-delete runs — old chunks survive.
    assert client.count(_COLLECTION).count == count_before


def test_ingest_source_removes_orphaned_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    many_pages = [
        PageText(page_number=1, text="core vaccines protect adult dogs from disease " * 60),
    ]
    monkeypatch.setattr("app.rag.ingest.read_pdf_pages", lambda path: many_pages)
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, _DIM, recreate=True)
    embedder = FakeEmbedder(_DIM)

    ingest_source(client, embedder, _COLLECTION, _source(), Path("/tmp"))
    assert client.count(_COLLECTION).count > 1


    monkeypatch.setattr(
        "app.rag.ingest.read_pdf_pages",
        lambda path: [PageText(page_number=1, text="short replacement text")],
    )
    ingest_source(client, embedder, _COLLECTION, _source(), Path("/tmp"))
    assert client.count(_COLLECTION).count == 1


def test_ingest_source_warns_on_zero_chunks(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        "app.rag.ingest.read_pdf_pages",
        lambda path: [PageText(page_number=1, text="   ")],
    )
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, _DIM, recreate=True)

    with caplog.at_level("WARNING"):
        assert ingest_source(client, FakeEmbedder(_DIM), _COLLECTION, _source(), Path("/tmp")) == 0
    assert any("no chunks" in record.message for record in caplog.records)


def test_ingest_source_with_blank_pages_returns_zero_without_deleting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    full_pages = [PageText(page_number=1, text="core vaccines protect dogs from disease")]
    monkeypatch.setattr("app.rag.ingest.read_pdf_pages", lambda path: full_pages)
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, _DIM, recreate=True)
    embedder = FakeEmbedder(_DIM)

    ingest_source(client, embedder, _COLLECTION, _source(), Path("/tmp"))
    count_before = client.count(_COLLECTION).count
    assert count_before > 0

    blank_pages = [PageText(page_number=1, text="   "), PageText(page_number=2, text="")]
    monkeypatch.setattr("app.rag.ingest.read_pdf_pages", lambda path: blank_pages)

    assert ingest_source(client, embedder, _COLLECTION, _source(), Path("/tmp")) == 0
    assert client.count(_COLLECTION).count == count_before

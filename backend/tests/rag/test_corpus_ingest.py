from __future__ import annotations

import sys
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from app.rag.chunking import PageText
from app.rag.fakes import FakeEmbedder
from app.rag.manifest import CorpusSource
from app.rag.store import ensure_collection
from scripts import corpus_ingest

pytestmark = pytest.mark.filterwarnings("ignore:Payload indexes have no effect")

_COLLECTION = "corpus_ingest_test"
_DIM = 16


def _source(source_id: str, file: str) -> CorpusSource:
    return CorpusSource(
        source_id=source_id,
        title="Doc",
        organization="Org",
        year=2024,
        url="https://example.org/doc.pdf",
        file=file,
        license_note=None,
    )


def test_recreate_with_source_id_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["corpus_ingest", "--recreate", "--source-id", "x"])
    with pytest.raises(SystemExit, match="--recreate rebuilds the entire collection"):
        corpus_ingest.main()


def test_recreate_with_limit_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["corpus_ingest", "--recreate", "--limit", "5"])
    with pytest.raises(SystemExit, match="--recreate rebuilds the entire collection"):
        corpus_ingest.main()


def test_ingest_all_isolates_per_source_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def _read(path: Path) -> list[PageText]:
        if path.name == "bad.pdf":
            raise RuntimeError("corrupt pdf")
        return [PageText(page_number=1, text="core vaccines protect adult dogs")]

    monkeypatch.setattr("app.rag.ingest.read_pdf_pages", _read)
    client = QdrantClient(":memory:")
    ensure_collection(client, _COLLECTION, _DIM, recreate=True)

    sources = [
        _source("good-1", "good1.pdf"),
        _source("bad", "bad.pdf"),
        _source("good-2", "good2.pdf"),
    ]
    total_chunks, failures = corpus_ingest.ingest_all(
        client, FakeEmbedder(_DIM), _COLLECTION, sources, Path("/tmp")
    )

    # The bad source is recorded but does not abort the run — both good sources ingest.
    assert total_chunks > 0
    assert [source_id for source_id, _ in failures] == ["bad"]
    assert client.count(_COLLECTION).count == total_chunks

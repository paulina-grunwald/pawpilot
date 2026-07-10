"""Push the vet corpus into the deployed backend's private Qdrant via the admin API.

Embeds locally (needs VERCEL_AI_GATEWAY in the environment / .env) and posts the
resulting points to ``POST /admin/rag/upsert``; the backend upserts them over its
private network, so Qdrant is never exposed publicly.

Run from ``backend/`` with the backend host + admin token supplied via the
environment (never hard-coded here):

    PAWPILOT_API_URL=https://<backend-host> \
    ADMIN_INGEST_TOKEN=<admin-token> \
        uv run python -m scripts.corpus_push --recreate
    ... --source-id <source-id>   # one source
    ... --limit 5                 # first 5 sources (smoke test)
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx

from app.rag.chunking import chunk_pages
from app.rag.config import get_rag_settings
from app.rag.embeddings import Embedder, GatewayEmbedder
from app.rag.ingest import build_points, read_pdf_pages
from app.rag.manifest import (
    CorpusSource,
    default_corpus_dir,
    load_manifest,
    resolve_source_tier,
)
from app.rag.observability import configure_langsmith
from app.rag.store import DENSE_VECTOR

_REQUEST_TIMEOUT_SECONDS = 180.0


def source_points(
    source: CorpusSource, embedder: Embedder, raw_dir: Path
) -> list[dict[str, object]]:
    """Chunk + embed one source into the wire form the admin endpoint expects."""
    pages = read_pdf_pages(raw_dir / source.file)
    records = chunk_pages(pages, chunk_size=1000, chunk_overlap=200)
    if not records:
        return []
    vectors = embedder.embed_documents([record.text for record in records])
    points = build_points(source, resolve_source_tier(source), records, vectors)
    return [
        {"id": str(point.id), "vector": point.vector[DENSE_VECTOR], "payload": point.payload}
        for point in points
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push the vet corpus to the deployed backend's admin upsert API."
    )
    parser.add_argument("--recreate", action="store_true", help="drop + rebuild the collection")
    parser.add_argument("--source-id", default=None, help="push only this source_id")
    parser.add_argument("--limit", type=int, default=None, help="push at most N sources")
    args = parser.parse_args()

    if args.recreate and (args.source_id or args.limit is not None):
        raise SystemExit(
            "--recreate rebuilds the entire collection and cannot be combined with "
            "--source-id or --limit."
        )

    api_url = os.environ.get("PAWPILOT_API_URL")
    token = os.environ.get("ADMIN_INGEST_TOKEN")
    if not api_url or not token:
        raise SystemExit("PAWPILOT_API_URL and ADMIN_INGEST_TOKEN must be set")

    configure_langsmith()
    settings = get_rag_settings()
    corpus_dir = default_corpus_dir()
    raw_dir = corpus_dir / "raw"
    sources = load_manifest(corpus_dir / "sources.json")
    if args.source_id:
        sources = [source for source in sources if source.source_id == args.source_id]
        if not sources:
            raise SystemExit(f"source_id not found in manifest: {args.source_id!r}")
    if args.limit is not None:
        sources = sources[: args.limit]

    embedder = GatewayEmbedder(settings)
    total_chunks = 0
    failures: list[tuple[str, Exception]] = []
    with httpx.Client(
        base_url=api_url,
        headers={"X-Admin-Token": token},
        timeout=httpx.Timeout(_REQUEST_TIMEOUT_SECONDS),
    ) as http_client:
        collection = http_client.post(
            "/admin/rag/collection",
            json={"vector_size": settings.embed_dimensions, "recreate": args.recreate},
        )
        collection.raise_for_status()
        print(f"collection ready: {collection.json()}")

        for index, source in enumerate(sources, start=1):
            try:
                points = source_points(source, embedder, raw_dir)
                if not points:
                    print(f"[{index}/{len(sources)}] {source.source_id}: 0 chunks (skipped)")
                    continue
                response = http_client.post(
                    "/admin/rag/upsert",
                    json={"source_id": source.source_id, "points": points},
                )
                response.raise_for_status()
                chunks = int(response.json()["upserted"])
            except Exception as error:  # isolate per-source failures, report at the end
                failures.append((source.source_id, error))
                print(f"[{index}/{len(sources)}] {source.source_id}: FAILED — {error}")
                continue
            total_chunks += chunks
            print(f"[{index}/{len(sources)}] {source.source_id}: {chunks} chunks")

    succeeded = len(sources) - len(failures)
    print(f"Done — {succeeded}/{len(sources)} sources, {total_chunks} chunks.")
    if failures:
        raise SystemExit(
            f"{len(failures)} source(s) failed: {[source_id for source_id, _ in failures]}"
        )


if __name__ == "__main__":
    main()

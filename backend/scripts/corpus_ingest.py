"""Ingest the veterinary corpus into Qdrant.

Run from ``backend/``:

    uv run python -m scripts.corpus_ingest                 # ingest all sources
    uv run python -m scripts.corpus_ingest --recreate      # rebuild the collection
    uv run python -m scripts.corpus_ingest --source-id wsava-vaccination-2024
    uv run python -m scripts.corpus_ingest --limit 5       # first 5 sources (smoke test)

Requires VERCEL_AI_GATEWAY + QDRANT_URL in the environment / .env.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from qdrant_client import QdrantClient

from app.rag.config import get_rag_settings
from app.rag.embeddings import Embedder, GatewayEmbedder
from app.rag.ingest import ingest_source
from app.rag.manifest import CorpusSource, default_corpus_dir, load_manifest
from app.rag.observability import configure_langsmith
from app.rag.store import ensure_collection


def ingest_all(
    client: QdrantClient,
    embedder: Embedder,
    collection: str,
    sources: list[CorpusSource],
    raw_dir: Path,
) -> tuple[int, list[tuple[str, Exception]]]:
    """Ingest every source, isolating failures so one bad PDF can't abort the run.

    Returns the total chunks upserted and a list of ``(source_id, error)`` for the
    sources that raised.
    """
    total_chunks = 0
    failures: list[tuple[str, Exception]] = []
    for index, source in enumerate(sources, start=1):
        try:
            chunks = ingest_source(client, embedder, collection, source, raw_dir)
        except Exception as error:  # isolate per-source failures, report them at the end
            failures.append((source.source_id, error))
            print(f"[{index}/{len(sources)}] {source.source_id}: FAILED — {error}")
            continue
        total_chunks += chunks
        print(f"[{index}/{len(sources)}] {source.source_id}: {chunks} chunks")
    return total_chunks, failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the vet corpus into Qdrant.")
    parser.add_argument("--recreate", action="store_true", help="drop + rebuild the collection")
    parser.add_argument("--source-id", default=None, help="ingest only this source_id")
    parser.add_argument("--limit", type=int, default=None, help="ingest at most N sources")
    args = parser.parse_args()

    if args.recreate and (args.source_id or args.limit is not None):
        raise SystemExit(
            "--recreate rebuilds the entire collection and cannot be combined with "
            "--source-id or --limit — that would drop every other source and re-ingest "
            "only the subset. Rebuild fully, or re-ingest the subset without --recreate."
        )

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

    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    embedder = GatewayEmbedder(settings)
    ensure_collection(
        client, settings.collection, settings.embed_dimensions, recreate=args.recreate
    )

    total_chunks, failures = ingest_all(client, embedder, settings.collection, sources, raw_dir)
    succeeded = len(sources) - len(failures)
    print(
        f"Done — {succeeded}/{len(sources)} sources, "
        f"{total_chunks} chunks into '{settings.collection}'."
    )
    if failures:
        raise SystemExit(
            f"{len(failures)} source(s) failed: {[source_id for source_id, _ in failures]}"
        )


if __name__ == "__main__":
    main()

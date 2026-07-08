"""Generate a RAGAS synthetic retrieval test set from the corpus
Builds prechunked documents from a sample of corpus PDFs, runs the RAGAS
``TestsetGenerator`` (single- + multi-hop), and writes a reviewed-pending JSONL
with ``user_input`` / ``reference`` / ``reference_contexts`` columns.

Run:  uv sync --group evals && uv run python -m evals.rag.synth --sources 12 --size 12
"""

from __future__ import annotations

import argparse
from pathlib import Path

from langchain_core.documents import Document
from ragas.testset import TestsetGenerator
from ragas.testset.transforms import CustomNodeFilter, default_transforms_for_prechunked

from app.rag.chunking import chunk_pages
from app.rag.ingest import read_pdf_pages
from app.rag.manifest import default_corpus_dir, load_manifest
from evals.rag.judge import build_generator_embeddings, build_generator_llm

OUTPUT_PATH = Path(__file__).resolve().parent / "datasets" / "synthetic_testset.jsonl"


def corpus_documents(num_sources: int, chunks_per_source: int) -> list[Document]:
    corpus_dir = default_corpus_dir()
    raw_dir = corpus_dir / "raw"
    sources = load_manifest(corpus_dir / "sources.json")[:num_sources]
    documents: list[Document] = []
    for source in sources:
        pages = read_pdf_pages(raw_dir / source.file)
        for record in chunk_pages(pages)[:chunks_per_source]:
            documents.append(
                Document(
                    page_content=record.text,
                    metadata={"source_id": source.source_id, "page": record.page_start},
                )
            )
    return documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a RAGAS synthetic retrieval test set.")
    parser.add_argument("--sources", type=int, default=12, help="number of corpus PDFs to sample")
    parser.add_argument("--chunks-per-source", type=int, default=6)
    parser.add_argument("--size", type=int, default=12, help="number of synthetic queries")
    args = parser.parse_args()

    generator_llm = build_generator_llm()
    generator_embeddings = build_generator_embeddings()
    transforms = [
        transform
        for transform in default_transforms_for_prechunked(
            llm=generator_llm, embedding_model=generator_embeddings
        )
        if not isinstance(transform, CustomNodeFilter)
    ]

    documents = corpus_documents(args.sources, args.chunks_per_source)
    generator = TestsetGenerator(llm=generator_llm, embedding_model=generator_embeddings)
    testset = generator.generate_with_chunks(
        chunks=documents, testset_size=args.size, transforms=transforms
    )

    dataframe = testset.to_pandas()
    dataframe.to_json(OUTPUT_PATH, orient="records", lines=True, force_ascii=False)
    print(f"Wrote {len(dataframe)} synthetic cases to {OUTPUT_PATH} (review before committing).")


if __name__ == "__main__":
    main()

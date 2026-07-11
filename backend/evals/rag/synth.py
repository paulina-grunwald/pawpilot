"""Generate RAGAS synthetic question candidates from the corpus (idea generator).

This is NOT the scored golden set. The scored generation set is the curated,
human-reviewed generation_golden.jsonl (see evals/rag/curate.py). This script
exists to surface candidate question phrasings from the corpus body text; a human
rewrites and reviews anything worth keeping before it becomes ground truth.

Earlier this script produced document-metadata trivia (author roles, funders,
affiliations) because it fed the generator the first chunks of each PDF (front
matter), stripped the quality filter, and let RAGAS invent bibliographic personas.
It now samples body chunks, keeps the CustomNodeFilter, pins a single dog-owner
persona, and runs single-hop only.

Run:  uv sync --group evals && uv run python -m evals.rag.synth --sources 12 --size 12
"""

from __future__ import annotations

import argparse
from pathlib import Path

from langchain_core.documents import Document
from ragas.testset import TestsetGenerator
from ragas.testset.persona import Persona
from ragas.testset.synthesizers.single_hop.specific import SingleHopSpecificQuerySynthesizer

from app.rag.chunking import chunk_pages
from app.rag.ingest import read_pdf_pages
from app.rag.manifest import default_corpus_dir, load_manifest
from evals.rag.judge import build_generator_embeddings, build_generator_llm

OUTPUT_PATH = Path(__file__).resolve().parent / "datasets" / "synth_candidates.jsonl"

# Skip page 1 (title, authors, funders, abstract); the front matter is what made
# the old set bibliographic trivia.
_FRONT_MATTER_PAGES = 1

DOG_OWNER_PERSONA = Persona(
    name="Dog Owner",
    role_description=(
        "A dog owner with no veterinary training asking practical, everyday questions "
        "about their dog's health, symptoms, nutrition, and care in plain, non-clinical "
        "language."
    ),
)


def corpus_documents(num_sources: int, chunks_per_source: int) -> list[Document]:
    corpus_dir = default_corpus_dir()
    raw_dir = corpus_dir / "raw"
    sources = load_manifest(corpus_dir / "sources.json")[:num_sources]
    documents: list[Document] = []
    for source in sources:
        pages = read_pdf_pages(raw_dir / source.file)
        body = [record for record in chunk_pages(pages) if record.page_start > _FRONT_MATTER_PAGES]
        for record in body[:chunks_per_source]:
            documents.append(
                Document(
                    page_content=record.text,
                    metadata={"source_id": source.source_id, "page": record.page_start},
                )
            )
    return documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate RAGAS synthetic question candidates.")
    parser.add_argument("--sources", type=int, default=12, help="number of corpus PDFs to sample")
    parser.add_argument("--chunks-per-source", type=int, default=6)
    parser.add_argument("--size", type=int, default=12, help="number of candidate questions")
    args = parser.parse_args()

    generator_llm = build_generator_llm()
    generator_embeddings = build_generator_embeddings()

    documents = corpus_documents(args.sources, args.chunks_per_source)
    # Keep the stock prechunked transforms (CustomNodeFilter drops low-value nodes).
    # Pin one dog-owner persona so questions are owner-voiced, not bibliographic.
    generator = TestsetGenerator(
        llm=generator_llm,
        embedding_model=generator_embeddings,
        persona_list=[DOG_OWNER_PERSONA],
    )
    # Single-hop only: no forced multi-hop joins across unrelated front-matter chunks.
    query_distribution = [(SingleHopSpecificQuerySynthesizer(llm=generator_llm), 1.0)]

    testset = generator.generate_with_chunks(
        chunks=documents, testset_size=args.size, query_distribution=query_distribution
    )

    dataframe = testset.to_pandas()
    dataframe.to_json(OUTPUT_PATH, orient="records", lines=True, force_ascii=False)
    print(f"Wrote {len(dataframe)} candidate questions to {OUTPUT_PATH}.")
    print("These are drafts: rewrite into owner-voice questions and review before use.")


if __name__ == "__main__":
    main()

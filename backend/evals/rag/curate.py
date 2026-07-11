"""Curate the RAGAS generation golden set from the hand-verified retrieval set.

Reuses the real dog-owner questions in retrieval_golden.json as user_input,
drafts an owner-facing reference answer grounded ONLY in each query's gold source
chunks, and writes a reviewed=false JSONL for human sign-off. Flip reviewed to
true per row after a human checks the answer; the generation eval scores reviewed
rows only (see evals/rag/generation.py).

This is the reproducible drafting harness. Drafts are a starting point, not ground
truth, so a human must review each one. To protect that review, the tool refuses
to overwrite an output file that already has reviewed rows unless you pass --force.

Run:
  uv sync --group evals
  uv run python -m evals.rag.curate               draft every query
  uv run python -m evals.rag.curate --limit 3     draft the first 3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.rag.chunking import chunk_pages
from app.rag.ingest import read_pdf_pages
from app.rag.manifest import CorpusSource, default_corpus_dir, load_manifest

DATASETS = Path(__file__).resolve().parent / "datasets"
RETRIEVAL_GOLDEN = DATASETS / "retrieval_golden.json"
OUTPUT_PATH = DATASETS / "generation_golden.jsonl"

# Skip page 1 (title, authors, funders, abstract) when grounding; the front matter
# is what contaminated the old synthetic set.
_FRONT_MATTER_PAGES = 1
_CHUNKS_PER_SOURCE = 4

_DRAFT_INSTRUCTION = (
    "You are drafting the ground-truth answer for a consumer dog-health assistant. "
    "Answer the owner's question in plain, non-clinical language a dog owner understands. "
    "Use ONLY the provided source excerpts; do not add facts that are not in them. "
    "Two to four sentences. No citations, no author or journal names, no disclaimer boilerplate."
)


class RetrievalCase(BaseModel):
    """One row of retrieval_golden.json (the seed queries)."""

    model_config = ConfigDict(extra="ignore")

    query: str
    expected_source_ids: list[str]
    note: str | None = None


class DraftedReference(BaseModel):
    """Structured output from the generator LLM."""

    reference: str


class GenerationCaseRow(BaseModel):
    """One curated row, written reviewed=false for human sign-off."""

    user_input: str
    reference: str
    reference_contexts: list[str]
    expected_source_ids: list[str]
    origin: str = "curated-draft"
    reviewed: bool = False


def load_retrieval_cases(path: Path = RETRIEVAL_GOLDEN) -> list[RetrievalCase]:
    return [
        RetrievalCase.model_validate(row) for row in json.loads(path.read_text(encoding="utf-8"))
    ]


def _sources_by_id() -> dict[str, CorpusSource]:
    corpus_dir = default_corpus_dir()
    return {source.source_id: source for source in load_manifest(corpus_dir / "sources.json")}


def gold_contexts(expected_source_ids: list[str], by_id: dict[str, CorpusSource]) -> list[str]:
    """Body chunks from each gold source (front matter skipped), for grounding."""
    raw_dir = default_corpus_dir() / "raw"
    contexts: list[str] = []
    for source_id in expected_source_ids:
        source = by_id.get(source_id)
        if source is None:
            continue
        pages = read_pdf_pages(raw_dir / source.file)
        body = [
            record.text for record in chunk_pages(pages) if record.page_start > _FRONT_MATTER_PAGES
        ]
        contexts.extend(body[:_CHUNKS_PER_SOURCE])
    return contexts


def draft_reference(generator_llm: Any, question: str, contexts: list[str]) -> str:
    excerpts = "\n\n".join(contexts)
    prompt = f"{_DRAFT_INSTRUCTION}\n\nQUESTION:\n{question}\n\nSOURCE EXCERPTS:\n{excerpts}"
    drafted = generator_llm.generate(prompt=prompt, response_model=DraftedReference)
    return str(drafted.reference).strip()


def _has_reviewed_rows(path: Path) -> bool:
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and json.loads(line).get("reviewed") is True:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Curate the generation golden set from retrieval_golden.json."
    )
    parser.add_argument("--limit", type=int, default=None, help="draft only the first N queries")
    parser.add_argument(
        "--force", action="store_true", help="overwrite even if the output has reviewed rows"
    )
    args = parser.parse_args()

    if _has_reviewed_rows(OUTPUT_PATH) and not args.force:
        raise SystemExit(
            f"Refusing to overwrite {OUTPUT_PATH}: it already has reviewed rows. Re-drafting would "
            "discard that review. Pass --force to overwrite anyway."
        )

    # Imported here so the module stays importable without the optional evals group.
    from evals.rag.judge import build_generator_llm

    retrieval_cases = load_retrieval_cases()
    if args.limit is not None:
        retrieval_cases = retrieval_cases[: args.limit]

    by_id = _sources_by_id()
    generator_llm = build_generator_llm()
    rows: list[GenerationCaseRow] = []
    for retrieval_case in retrieval_cases:
        contexts = gold_contexts(retrieval_case.expected_source_ids, by_id)
        reference = draft_reference(generator_llm, retrieval_case.query, contexts)
        rows.append(
            GenerationCaseRow(
                user_input=retrieval_case.query,
                reference=reference,
                reference_contexts=contexts,
                expected_source_ids=retrieval_case.expected_source_ids,
            )
        )
        print(f"drafted: {retrieval_case.query}")

    payload = "\n".join(row.model_dump_json() for row in rows) + "\n"
    OUTPUT_PATH.write_text(payload, encoding="utf-8")
    print(f"\nWrote {len(rows)} draft cases to {OUTPUT_PATH}.")
    print("Review each reference, then set reviewed=true.")


if __name__ == "__main__":
    main()

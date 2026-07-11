"""Dataset loader for the RAGAS generation eval.

generation_golden.jsonl holds owner-facing questions and human-reviewed reference
answers the judge scores the agent against. It is curated from the retrieval
golden set (see evals/rag/curate.py): the questions are real dog-owner intents,
the references are owner-facing answers grounded in the gold corpus sources.

Only rows with reviewed set to true are scored. A freshly drafted row is
reviewed=false, so an unreviewed draft never silently becomes ground truth; flip
it to true after a human checks the answer.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

GENERATION_PATH = Path(__file__).resolve().parent / "datasets" / "generation_golden.jsonl"


class GenerationCase(BaseModel):
    """One question plus its reviewed reference answer to score the agent against."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    user_input: str
    reference: str
    reviewed: bool = False


def load_generation_cases(
    path: Path = GENERATION_PATH, *, reviewed_only: bool = True
) -> list[GenerationCase]:
    """Load the generation golden set, one GenerationCase per non-blank JSONL line.

    Returns an empty list when the file is absent (mirrors the retrieval loader);
    the runner reports that as "no dataset" rather than silently scoring nothing.
    A row missing user_input or reference fails loud with a ValidationError.

    By default only reviewed=true rows are returned, so unreviewed drafts are
    never scored. Pass reviewed_only=false to load every row (curation tooling).
    """
    if not path.exists():
        return []
    cases = [
        GenerationCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if reviewed_only:
        return [case for case in cases if case.reviewed]
    return cases

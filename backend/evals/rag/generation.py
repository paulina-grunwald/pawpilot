"""Dataset loader for the RAGAS generation eval.

synthetic_testset.jsonl carries the questions and reference answers the judge
scores the agent against. Each row also has retrieval/persona metadata, but only
user_input (the question) and reference (the ground-truth answer) matter for
generation metrics - so GenerationCase keeps just those two and drops the rest.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

GENERATION_PATH = Path(__file__).resolve().parent / "datasets" / "synthetic_testset.jsonl"


class GenerationCase(BaseModel):
    """One question + reference answer to score the agent's response against."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    user_input: str
    reference: str


def load_generation_cases(path: Path = GENERATION_PATH) -> list[GenerationCase]:
    """Load the synthetic test set, one GenerationCase per non-blank JSONL line.

    Returns an empty list when the file is absent (mirrors the retrieval loader);
    the runner reports that as "no dataset" rather than silently scoring nothing.
    A row missing user_input or reference fails loud with a ValidationError.
    """
    if not path.exists():
        return []
    return [
        GenerationCase.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

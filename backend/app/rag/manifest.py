"""Corpus manifest loading + `source_tier` resolution.

The manifest is the committed ``data/corpus/sources.json`` (the PDFs themselves
stay gitignored, rebuildable from it). Each source resolves to a `source_tier`
so advice surfaces can prefer guideline-grade sources over single primary
studies — from an explicit ``source_tier`` field if present, else a heuristic on
organization / lane / id.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from app.rag.schemas import SourceTier

# Substring markers (matched case-insensitively against the organization name).
_GUIDELINE_ORG_MARKERS = (
    "wsava",
    "aaha",
    "animal hospital association",
    "recover",
    "esccap",
    "heartworm",
    "aidap",
    "australian veterinary association",
)
_CONSENSUS_ORG_MARKERS = ("acvim", "task force")
_FOOD_LANES = frozenset({"food", "dogfood", "nutrition-product"})


class CorpusSource(BaseModel):
    """One row of ``sources.json`` (tolerant of extra/optional fields)."""

    model_config = ConfigDict(extra="ignore")

    source_id: str
    title: str
    organization: str
    year: int | str | None = None
    url: str
    file: str
    bytes: int | None = None
    pages: int | None = None
    license_note: str | None = None
    status: str | None = None
    lane: str | None = None
    topic: str | None = None
    # Explicit override — wins over the heuristic when set.
    source_tier: SourceTier | None = None


def resolve_source_tier(source: CorpusSource) -> SourceTier:
    """Resolve a source's tier (explicit field if present, else heuristic)."""
    if source.source_tier is not None:
        return source.source_tier

    source_id = source.source_id.lower()
    organization = source.organization.lower()
    title = source.title.lower()
    lane = (source.lane or "").lower()

    if source_id.startswith("breed-") or lane == "breed":
        return "breed"
    # Guideline before consensus: guideline-body docs (WSAVA/AAHA/COAST) whose title
    # says "consensus" must tier as guideline, not be excluded by a guideline filter.
    if (
        any(marker in organization for marker in _GUIDELINE_ORG_MARKERS)
        or "guideline" in title
        or "toolkit" in title
    ):
        return "guideline"
    if "consensus" in title or any(marker in organization for marker in _CONSENSUS_ORG_MARKERS):
        return "consensus"
    if lane in _FOOD_LANES:
        return "food"
    return "primary_research"


def default_corpus_dir() -> Path:
    """The repo-root ``data/corpus`` directory (resolved from this file)."""
    return Path(__file__).resolve().parents[3] / "data" / "corpus"


def load_manifest(path: Path | None = None) -> list[CorpusSource]:
    """Load + validate the corpus manifest, rejecting duplicate ``source_id``s."""
    manifest_path = path if path is not None else default_corpus_dir() / "sources.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = raw["sources"] if isinstance(raw, dict) else raw

    sources: list[CorpusSource] = []
    seen: set[str] = set()
    for row in rows:
        source = CorpusSource.model_validate(row)
        if source.source_id in seen:
            raise ValueError(f"duplicate source_id in manifest: {source.source_id}")
        seen.add(source.source_id)
        sources.append(source)
    return sources

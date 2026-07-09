"""Exact-match lookup tools: breed norms + toxic substances.

These are *tools, not chunks* — for "is xylitol toxic to dogs" an exact alias
lookup beats fuzzy retrieval, and returning ``None`` for unknowns lets the
agent (spec 010) abstain instead of guessing.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.rag.schemas import BreedNorm, SizeCategory, ToxicSubstance

_DATA_DIR = Path(__file__).resolve().parent / "data"

# Upper-bound grams per category; >= the last bound falls through to "giant".
_SIZE_THRESHOLDS_GRAMS: tuple[tuple[int, SizeCategory], ...] = (
    (5000, "toy"),
    (10000, "small"),
    (25000, "medium"),
    (45000, "large"),
)


@lru_cache
def _breed_norms() -> tuple[BreedNorm, ...]:
    rows = json.loads((_DATA_DIR / "breed_norms.json").read_text(encoding="utf-8"))
    return tuple(BreedNorm.model_validate(row) for row in rows)


@lru_cache
def _toxic_substances() -> tuple[ToxicSubstance, ...]:
    rows = json.loads((_DATA_DIR / "toxic_substances.json").read_text(encoding="utf-8"))
    return tuple(ToxicSubstance.model_validate(row) for row in rows)


@lru_cache
def _toxicity_index() -> dict[str, ToxicSubstance]:
    index: dict[str, ToxicSubstance] = {}
    for substance in _toxic_substances():
        for key in (substance.name, *substance.aliases):
            index[key.strip().lower()] = substance
    return index


def size_category_for_weight(weight_grams: int) -> SizeCategory:
    """Derive a size category from weight (fallback for mixed/unknown breeds)."""
    for threshold, category in _SIZE_THRESHOLDS_GRAMS:
        if weight_grams < threshold:
            return category
    return "giant"


def lookup_breed_norm(
    *,
    breed: str | None = None,
    size_category: SizeCategory | None = None,
) -> BreedNorm | None:
    """Look up norms by breed name (preferred) then by size category."""
    norms = _breed_norms()
    if breed is not None:
        key = breed.strip().lower()
        for norm in norms:
            if norm.breed is not None and norm.breed.lower() == key:
                return norm
    if size_category is not None:
        for norm in norms:
            if norm.breed is None and norm.size_category == size_category:
                return norm
    return None


def lookup_toxicity(name: str) -> ToxicSubstance | None:
    """Match a substance by name or alias, case-insensitively; ``None`` if unknown."""
    return _toxicity_index().get(name.strip().lower())

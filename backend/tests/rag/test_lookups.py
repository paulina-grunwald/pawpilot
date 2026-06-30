from __future__ import annotations

import pytest

from app.rag.lookups import (
    _breed_norms,
    _toxic_substances,
    lookup_breed_norm,
    lookup_toxicity,
    size_category_for_weight,
)


def test_all_breed_norm_rows_parse_with_source_urls() -> None:
    norms = _breed_norms()
    assert len(norms) >= 5
    assert all(norm.source_url for norm in norms)
    # every size category is represented by a canonical (breed=None) row
    canonical = {norm.size_category for norm in norms if norm.breed is None}
    assert canonical == {"toy", "small", "medium", "large", "giant"}


def test_all_toxic_rows_parse_with_source_urls() -> None:
    substances = _toxic_substances()
    assert len(substances) >= 20
    assert all(substance.source_url for substance in substances)
    assert all(substance.notes for substance in substances)


@pytest.mark.parametrize(
    ("query", "expected_name"),
    [
        ("chocolate", "chocolate"),
        ("Chocolate", "chocolate"),
        ("  XYLITOL  ", "xylitol"),
        ("birch sugar", "xylitol"),
        ("raisins", "grapes"),
        ("advil", "ibuprofen"),
        ("tylenol", "acetaminophen"),
        ("ethylene glycol", "antifreeze"),
    ],
)
def test_toxicity_lookup_hits(query: str, expected_name: str) -> None:
    substance = lookup_toxicity(query)
    assert substance is not None
    assert substance.name == expected_name


def test_toxicity_lookup_unknown_returns_none() -> None:
    assert lookup_toxicity("kibble") is None
    assert lookup_toxicity("Bavarian Mist Retriever") is None


def test_breed_norm_by_named_breed() -> None:
    norm = lookup_breed_norm(breed="Australian Shepherd")
    assert norm is not None
    assert norm.breed == "Australian Shepherd"
    assert norm.size_category == "medium"
    assert norm.daily_walk_target_km_range == (5.0, 12.0)


def test_breed_norm_by_named_breed_is_case_insensitive() -> None:
    norm = lookup_breed_norm(breed="border collie")
    assert norm is not None
    assert norm.breed == "Border Collie"


def test_breed_norm_falls_back_to_size_category() -> None:
    norm = lookup_breed_norm(breed="Some Unknown Mix", size_category="large")
    assert norm is not None
    assert norm.breed is None
    assert norm.size_category == "large"


def test_breed_norm_unknown_returns_none() -> None:
    assert lookup_breed_norm(breed="Some Unknown Mix") is None
    assert lookup_breed_norm() is None


@pytest.mark.parametrize(
    ("weight_grams", "expected"),
    [
        (3000, "toy"),
        (7000, "small"),
        (20000, "medium"),
        (35000, "large"),
        (60000, "giant"),
    ],
)
def test_size_category_for_weight(weight_grams: int, expected: str) -> None:
    assert size_category_for_weight(weight_grams) == expected

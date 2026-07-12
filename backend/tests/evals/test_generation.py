"""Tests for the RAGAS generation dataset loader.

Cover the GenerationCase model (fields, frozen, extra-key tolerance, required
fields) and load_generation_cases (missing file, blank-line skipping, malformed
rows, the reviewed-only filter, and that the committed golden set parses).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evals.rag.generation import GenerationCase, load_generation_cases

# --------------------------------------------------------------------------- #
# GenerationCase
# --------------------------------------------------------------------------- #


def test_generation_case_holds_fields() -> None:
    case = GenerationCase(user_input="How often do boosters go?", reference="Every three years.")
    assert case.user_input == "How often do boosters go?"
    assert case.reference == "Every three years."


def test_generation_case_is_frozen() -> None:
    case = GenerationCase(user_input="q", reference="a")
    with pytest.raises(ValidationError):
        case.reference = "changed"


def test_generation_case_defaults_reviewed_false() -> None:
    case = GenerationCase(user_input="q", reference="a")
    assert case.reviewed is False


def test_generation_case_ignores_dataset_metadata_columns() -> None:
    case = GenerationCase.model_validate(
        {
            "user_input": "q",
            "reference": "a",
            "reference_contexts": ["ctx"],
            "persona_name": "curious owner",
            "query_style": "direct",
            "query_length": "short",
            "synthesizer_name": "single_hop",
        }
    )
    assert case.user_input == "q"
    assert case.reference == "a"


def test_generation_case_requires_reference() -> None:
    with pytest.raises(ValidationError):
        GenerationCase.model_validate({"user_input": "q"})


def test_generation_case_requires_user_input() -> None:
    with pytest.raises(ValidationError):
        GenerationCase.model_validate({"reference": "a"})


# --------------------------------------------------------------------------- #
# load_generation_cases
# --------------------------------------------------------------------------- #


def test_load_returns_empty_when_file_missing(tmp_path: Path) -> None:
    assert load_generation_cases(tmp_path / "absent.jsonl") == []


def test_load_parses_rows_and_skips_blank_lines(tmp_path: Path) -> None:
    dataset = tmp_path / "testset.jsonl"
    dataset.write_text(
        json.dumps(
            {"user_input": "q1", "reference": "a1", "reviewed": True, "persona_name": "owner"}
        )
        + "\n\n"
        + json.dumps(
            {"user_input": "q2", "reference": "a2", "reviewed": True, "reference_contexts": ["c"]}
        )
        + "\n",
        encoding="utf-8",
    )
    cases = load_generation_cases(dataset)
    assert [(case.user_input, case.reference) for case in cases] == [("q1", "a1"), ("q2", "a2")]


def test_load_filters_unreviewed_rows_by_default(tmp_path: Path) -> None:
    dataset = tmp_path / "testset.jsonl"
    dataset.write_text(
        json.dumps({"user_input": "q1", "reference": "a1", "reviewed": True})
        + "\n"
        + json.dumps({"user_input": "q2", "reference": "a2", "reviewed": False})
        + "\n",
        encoding="utf-8",
    )
    assert [case.user_input for case in load_generation_cases(dataset)] == ["q1"]


def test_load_treats_missing_reviewed_as_unreviewed(tmp_path: Path) -> None:
    dataset = tmp_path / "testset.jsonl"
    dataset.write_text(json.dumps({"user_input": "q1", "reference": "a1"}) + "\n", encoding="utf-8")
    assert load_generation_cases(dataset) == []


def test_load_returns_all_rows_when_reviewed_only_false(tmp_path: Path) -> None:
    dataset = tmp_path / "testset.jsonl"
    dataset.write_text(
        json.dumps({"user_input": "q1", "reference": "a1", "reviewed": True})
        + "\n"
        + json.dumps({"user_input": "q2", "reference": "a2", "reviewed": False})
        + "\n",
        encoding="utf-8",
    )
    cases = load_generation_cases(dataset, reviewed_only=False)
    assert [case.user_input for case in cases] == ["q1", "q2"]


def test_load_raises_on_row_missing_reference(tmp_path: Path) -> None:
    dataset = tmp_path / "testset.jsonl"
    dataset.write_text(json.dumps({"user_input": "q1"}) + "\n", encoding="utf-8")
    with pytest.raises(ValidationError):
        load_generation_cases(dataset)


def test_load_reads_committed_golden_set() -> None:
    cases = load_generation_cases()
    assert cases, "committed generation_golden.jsonl should have reviewed rows"
    assert all(case.user_input.strip() and case.reference.strip() for case in cases)
    assert all(case.reviewed for case in cases)

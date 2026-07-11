"""Tests for the RAGAS generation-metric wiring.

Hermetic - no keys, no RAGAS install. The live metrics are faked with recording
doubles so the scorer's routing (which sample field reaches which metric) is
pinned exactly to the probed .ascore signatures.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from app.agent.prompt import VET_DISCLAIMER
from app.agent.red_flags import EMERGENCY_BANNER
from evals.rag.generation_metrics import (
    GENERATION_METRIC_NAMES,
    GenerationSample,
    GenerationScorer,
    GenerationScores,
    strip_boilerplate,
)

# --------------------------------------------------------------------------- #
# strip_boilerplate
# --------------------------------------------------------------------------- #


def test_strip_removes_banner_and_keeps_answer() -> None:
    answer = "Boost every three years [S1]."
    assert strip_boilerplate(EMERGENCY_BANNER + answer) == answer


def test_strip_removes_trailing_disclaimer() -> None:
    answer = "Boost every three years [S1]."
    assert strip_boilerplate(f"{answer} {VET_DISCLAIMER}") == answer


def test_strip_removes_both_banner_and_disclaimer() -> None:
    answer = "Boost every three years [S1]."
    assert strip_boilerplate(f"{EMERGENCY_BANNER}{answer} {VET_DISCLAIMER}") == answer


def test_strip_is_noop_without_boilerplate() -> None:
    answer = "A perfectly ordinary answer."
    assert strip_boilerplate(answer) == answer


def test_strip_handles_empty_string() -> None:
    assert strip_boilerplate("") == ""


def test_strip_only_removes_a_leading_banner() -> None:
    # A banner that appears mid-text (not as the prefix) is left untouched.
    text = "Intro. " + EMERGENCY_BANNER + "tail"
    assert strip_boilerplate(text) == text


# --------------------------------------------------------------------------- #
# GENERATION_METRIC_NAMES stays in sync with GenerationScores
# --------------------------------------------------------------------------- #


def test_metric_names_match_scores_fields() -> None:
    assert tuple(GenerationScores.model_fields) == GENERATION_METRIC_NAMES


# --------------------------------------------------------------------------- #
# GenerationScorer.ascore - routing and result assembly
# --------------------------------------------------------------------------- #


class _RecordingMetric:
    """A fake RAGAS metric: records ascore kwargs and returns a fixed value."""

    def __init__(self, value: float) -> None:
        self._value = value
        self.calls: list[dict[str, Any]] = []

    async def ascore(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(value=self._value)


def _sample() -> GenerationSample:
    return GenerationSample(
        user_input="How often are boosters needed?",
        response="Every three years [S1].",
        retrieved_contexts=["Adult dogs need a booster every three years.", "Puppies differ."],
        reference="Every three years for adult dogs.",
    )


async def test_ascore_assembles_scores_from_each_metric_value() -> None:
    scorer = GenerationScorer(
        faithfulness=_RecordingMetric(0.9),
        answer_accuracy=_RecordingMetric(0.8),
        answer_relevancy=_RecordingMetric(0.7),
        noise_sensitivity=_RecordingMetric(0.1),
    )
    scores = await scorer.ascore(_sample())
    assert scores == GenerationScores(
        faithfulness=0.9, answer_accuracy=0.8, answer_relevancy=0.7, noise_sensitivity=0.1
    )


async def test_ascore_routes_sample_fields_to_the_right_metric_inputs() -> None:
    faithfulness = _RecordingMetric(0.9)
    answer_accuracy = _RecordingMetric(0.8)
    answer_relevancy = _RecordingMetric(0.7)
    noise_sensitivity = _RecordingMetric(0.1)
    scorer = GenerationScorer(
        faithfulness=faithfulness,
        answer_accuracy=answer_accuracy,
        answer_relevancy=answer_relevancy,
        noise_sensitivity=noise_sensitivity,
    )
    sample = _sample()

    await scorer.ascore(sample)

    # faithfulness: no reference; needs the contexts.
    assert faithfulness.calls[0] == {
        "user_input": sample.user_input,
        "response": sample.response,
        "retrieved_contexts": sample.retrieved_contexts,
    }
    # answer_accuracy: needs the reference; no contexts.
    assert answer_accuracy.calls[0] == {
        "user_input": sample.user_input,
        "response": sample.response,
        "reference": sample.reference,
    }
    # answer_relevancy: question + answer only.
    assert answer_relevancy.calls[0] == {
        "user_input": sample.user_input,
        "response": sample.response,
    }
    # noise_sensitivity: everything.
    assert noise_sensitivity.calls[0] == {
        "user_input": sample.user_input,
        "response": sample.response,
        "reference": sample.reference,
        "retrieved_contexts": sample.retrieved_contexts,
    }


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #


def test_generation_sample_is_frozen() -> None:
    sample = _sample()
    with pytest.raises(ValidationError):
        sample.response = "changed"


def test_generation_scores_is_frozen() -> None:
    scores = GenerationScores(
        faithfulness=1.0, answer_accuracy=1.0, answer_relevancy=1.0, noise_sensitivity=0.0
    )
    with pytest.raises(ValidationError):
        scores.faithfulness = 0.5

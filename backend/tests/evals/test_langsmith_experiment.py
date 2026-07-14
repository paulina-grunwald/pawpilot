"""Tests for the LangSmith Datasets and Experiments adapters.

Hermetic: no LangSmith client, no network. The example builders, targets, and
evaluators are exercised directly; the agent runs on a scripted model and the
retriever is a stub, so the whole aevaluate wiring is validated without creds.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from langchain_core.messages import AIMessage

from app.agent.prompt import VET_DISCLAIMER
from app.rag.retriever import VetCorpusRetriever
from evals.rag.agent_eval import EvalAgent
from evals.rag.generation import GenerationCase
from evals.rag.generation_metrics import GenerationScorer
from evals.rag.golden import DEFAULT_KS, GoldenQuery
from evals.rag.langsmith_experiment import (
    LangSmithCredentialsError,
    generation_examples,
    generation_target,
    make_generation_evaluator,
    recall_at_k_by_ids,
    recall_evaluator,
    require_langsmith,
    retrieval_examples,
    retrieval_target,
)
from tests.agent.conftest import (
    StubRetriever,
    build_test_agent,
    make_agent_settings,
    make_chunk,
    tool_call_message,
)


class _RecordingMetric:
    """A fake RAGAS metric returning a fixed value (matches the real ascore shape)."""

    def __init__(self, value: float) -> None:
        self._value = value

    async def ascore(self, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(value=self._value)


def _scorer(
    faithfulness: float = 0.9,
    answer_accuracy: float = 0.8,
    answer_relevancy: float = 0.7,
    noise_sensitivity: float = 0.1,
) -> GenerationScorer:
    return GenerationScorer(
        faithfulness=_RecordingMetric(faithfulness),
        answer_accuracy=_RecordingMetric(answer_accuracy),
        answer_relevancy=_RecordingMetric(answer_relevancy),
        noise_sensitivity=_RecordingMetric(noise_sensitivity),
    )


# --------------------------------------------------------------------------- #
# example builders
# --------------------------------------------------------------------------- #


def test_generation_examples_maps_inputs_and_outputs() -> None:
    cases = [GenerationCase(user_input="q1", reference="a1", reviewed=True)]
    assert generation_examples(cases) == [
        {"inputs": {"user_input": "q1"}, "outputs": {"reference": "a1"}}
    ]


def test_retrieval_examples_maps_inputs_and_outputs() -> None:
    golden = [GoldenQuery(query="How often?", expected_source_ids=["s1", "s2"])]
    assert retrieval_examples(golden) == [
        {"inputs": {"query": "How often?"}, "outputs": {"expected_source_ids": ["s1", "s2"]}}
    ]


# --------------------------------------------------------------------------- #
# generation target
# --------------------------------------------------------------------------- #


async def test_generation_target_returns_answer_and_contexts() -> None:
    passage = "Adult dogs need a booster every three years."
    agent = EvalAgent(
        build_test_agent(
            responses=[
                tool_call_message("retrieve_vet_corpus", "boosters"),
                AIMessage(content=f"Every three years [S1]. {VET_DISCLAIMER}"),
            ],
            chunks=[make_chunk(text=passage)],
        )
    )
    output = await generation_target(agent, {"user_input": "How often are boosters needed?"})
    assert output["budget_exhausted"] is False
    assert "Every three years [S1]." in output["response"]
    assert not output["response"].endswith(VET_DISCLAIMER)  # boilerplate stripped before scoring
    assert output["retrieved_contexts"] == [passage]


async def test_generation_target_flags_budget_exhausted() -> None:
    agent = EvalAgent(
        build_test_agent(
            responses=[tool_call_message("retrieve_vet_corpus", "loop")],
            chunks=[make_chunk()],
            settings=make_agent_settings(agent_max_tool_calls=1),
        )
    )
    output = await generation_target(agent, {"user_input": "Tell me everything."})
    assert output["budget_exhausted"] is True


# --------------------------------------------------------------------------- #
# generation evaluator
# --------------------------------------------------------------------------- #


async def test_generation_evaluator_scores_all_four_metrics() -> None:
    evaluate = make_generation_evaluator(_scorer(0.9, 0.8, 0.7, 0.1))
    run = SimpleNamespace(
        outputs={
            "response": "Every three years [S1].",
            "retrieved_contexts": ["ctx"],
            "budget_exhausted": False,
        }
    )
    example = SimpleNamespace(
        inputs={"user_input": "How often?"}, outputs={"reference": "Every 3 years."}
    )
    result = await evaluate(run, example)
    assert result["results"] == [
        {"key": "faithfulness", "score": 0.9},
        {"key": "answer_accuracy", "score": 0.8},
        {"key": "answer_relevancy", "score": 0.7},
        {"key": "noise_sensitivity", "score": 0.1},
    ]


async def test_generation_evaluator_skips_budget_exhausted_row() -> None:
    evaluate = make_generation_evaluator(_scorer())
    run = SimpleNamespace(outputs={"budget_exhausted": True})
    example = SimpleNamespace(inputs={"user_input": "q"}, outputs={"reference": "r"})
    assert await evaluate(run, example) == {"results": []}


# --------------------------------------------------------------------------- #
# retrieval target + recall
# --------------------------------------------------------------------------- #


def test_retrieval_target_returns_ordered_source_ids() -> None:
    retriever = cast(
        VetCorpusRetriever,
        StubRetriever([make_chunk(source_id="s1"), make_chunk(source_id="s2")]),
    )
    assert retrieval_target(retriever, {"query": "q"}) == {"retrieved_source_ids": ["s1", "s2"]}


def test_recall_at_k_by_ids_respects_the_cutoff() -> None:
    assert recall_at_k_by_ids(["s2"], ["s1", "s2", "s3"], k=1) == 0.0  # s2 is below the top-1
    assert recall_at_k_by_ids(["s2"], ["s1", "s2", "s3"], k=2) == 1.0
    assert recall_at_k_by_ids([], ["s1"], k=5) == 0.0  # nothing expected -> a miss


def test_recall_evaluator_scores_each_k() -> None:
    run = SimpleNamespace(outputs={"retrieved_source_ids": ["s9", "s2"]})
    example = SimpleNamespace(outputs={"expected_source_ids": ["s2"]})
    result = recall_evaluator(run, example)
    assert [entry["key"] for entry in result["results"]] == [f"recall@{k}" for k in DEFAULT_KS]
    assert all(entry["score"] == 1.0 for entry in result["results"])  # s2 is within every cutoff


# --------------------------------------------------------------------------- #
# credential guard
# --------------------------------------------------------------------------- #


def test_require_langsmith_raises_without_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    with pytest.raises(LangSmithCredentialsError):
        require_langsmith()


def test_require_langsmith_raises_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    with pytest.raises(LangSmithCredentialsError):
        require_langsmith()


def test_require_langsmith_passes_with_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "ls-key")
    require_langsmith()

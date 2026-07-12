"""Tests for the agent generation-eval runner.

The pure cores (aggregation, summary, markdown, baseline writer) are tested
directly. run_eval is driven through the *real* agent graph with a scripted
model - so the emergency-banner strip, budget-exhaustion skip, and context
capture are exercised end-to-end - against a real GenerationScorer whose
metrics are recording fakes (no keys, no RAGAS install).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from langchain_core.messages import AIMessage

from app.agent.prompt import VET_DISCLAIMER
from app.agent.red_flags import EMERGENCY_BANNER
from app.agent.runner import _BUDGET_EXHAUSTED_MESSAGE as BUDGET_EXHAUSTED_MESSAGE
from app.agent.schemas import AgentAnswer
from evals.rag.agent_eval import EvalAgent
from evals.rag.generation import GenerationCase
from evals.rag.generation_metrics import (
    GENERATION_METRIC_NAMES,
    GenerationSample,
    GenerationScorer,
    GenerationScores,
)
from evals.rag.run_agent_eval import (
    CaseResult,
    _format_score,
    _truncate,
    aggregate_means,
    render_markdown,
    run_eval,
    summarize_report,
    write_generation_baseline,
)
from tests.agent.conftest import (
    RaisingChatModel,
    build_test_agent,
    make_agent_settings,
    make_chunk,
    tool_call_message,
)


def _scores(
    faithfulness: float, answer_accuracy: float, answer_relevancy: float, noise_sensitivity: float
) -> GenerationScores:
    return GenerationScores(
        faithfulness=faithfulness,
        answer_accuracy=answer_accuracy,
        answer_relevancy=answer_relevancy,
        noise_sensitivity=noise_sensitivity,
    )


def _result(
    *,
    emergency: bool = False,
    budget: bool = False,
    errored: bool = False,
    scores: GenerationScores | None = None,
) -> CaseResult:
    return CaseResult(
        user_input="q",
        emergency=emergency,
        budget_exhausted=budget,
        errored=errored,
        scores=scores,
    )


class _RecordingMetric:
    """Fake RAGAS metric: records ascore kwargs, returns a fixed value."""

    def __init__(self, value: float) -> None:
        self._value = value
        self.calls: list[dict[str, Any]] = []

    async def ascore(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(value=self._value)


def _recording_scorer() -> tuple[GenerationScorer, dict[str, _RecordingMetric]]:
    metrics = {name: _RecordingMetric(0.5) for name in GENERATION_METRIC_NAMES}
    scorer = GenerationScorer(
        faithfulness=metrics["faithfulness"],
        answer_accuracy=metrics["answer_accuracy"],
        answer_relevancy=metrics["answer_relevancy"],
        noise_sensitivity=metrics["noise_sensitivity"],
    )
    return scorer, metrics


# --------------------------------------------------------------------------- #
# aggregate_means
# --------------------------------------------------------------------------- #


def test_aggregate_means_averages_each_metric() -> None:
    means = aggregate_means([_scores(1.0, 0.5, 0.8, 0.2), _scores(0.0, 0.5, 0.6, 0.0)])
    assert means == {
        "faithfulness": 0.5,
        "answer_accuracy": 0.5,
        "answer_relevancy": 0.7,
        "noise_sensitivity": 0.1,
    }


def test_aggregate_means_skips_nan_per_metric() -> None:
    nan = float("nan")
    means = aggregate_means([_scores(nan, 0.4, 0.8, 0.2), _scores(1.0, 0.6, 0.6, 0.0)])
    assert means["faithfulness"] == 1.0  # the NaN row is skipped for this metric only
    assert means["answer_accuracy"] == 0.5


def test_aggregate_means_none_when_all_values_nan() -> None:
    nan = float("nan")
    means = aggregate_means([_scores(nan, nan, nan, nan)])
    assert means == {name: None for name in GENERATION_METRIC_NAMES}


def test_aggregate_means_empty_is_all_none() -> None:
    assert aggregate_means([]) == {name: None for name in GENERATION_METRIC_NAMES}


# --------------------------------------------------------------------------- #
# summarize_report
# --------------------------------------------------------------------------- #


def test_summarize_report_counts_and_means() -> None:
    results = [
        _result(scores=_scores(1.0, 1.0, 1.0, 0.0)),
        _result(emergency=True, scores=_scores(0.0, 0.0, 0.0, 0.2)),
        _result(budget=True),
        _result(errored=True),
    ]
    report = summarize_report("dense", results)
    assert report.mode == "dense"
    assert report.total_cases == 4
    assert report.scored_cases == 2
    assert report.budget_exhausted == 1
    assert report.errors == 1
    assert report.emergency == 1
    assert report.means["faithfulness"] == 0.5


# --------------------------------------------------------------------------- #
# render_markdown
# --------------------------------------------------------------------------- #


def test_render_markdown_has_summary_table_and_percase() -> None:
    results = [
        _result(scores=_scores(0.9, 0.8, 0.7, 0.1)),
        _result(budget=True),
        _result(errored=True),
    ]
    markdown = render_markdown(summarize_report("dense", results), results)
    assert "# Agent RAGAS - dense" in markdown
    assert "budget-exhausted (excluded): 1" in markdown
    assert "errored (excluded): 1" in markdown
    assert "noise_sensitivity (lower better)" in markdown
    assert "## Per-case" in markdown
    assert "## Conclusions" in markdown
    assert "-" in markdown



def test_write_generation_baseline_round_trips(tmp_path: Path) -> None:
    destination = tmp_path / "baselines.json"
    report = summarize_report("dense", [_result(scores=_scores(0.9, 0.8, 0.7, 0.1))])
    write_generation_baseline(report, destination)
    written = json.loads(destination.read_text())
    assert written["generation"]["dense"]["means"]["faithfulness"] == 0.9
    assert written["generation"]["dense"]["scored_cases"] == 1


def test_write_generation_baseline_preserves_retrieval_and_other_modes(tmp_path: Path) -> None:
    destination = tmp_path / "baselines.json"
    destination.write_text(
        json.dumps(
            {
                "retrieval": {"golden": {"recall@5": 0.5}},
                "generation": {"hybrid": {"mode": "hybrid"}},
            }
        )
    )
    report = summarize_report("dense", [_result(scores=_scores(0.9, 0.8, 0.7, 0.1))])
    write_generation_baseline(report, destination)
    written = json.loads(destination.read_text())
    assert written["retrieval"]["golden"]["recall@5"] == 0.5
    assert written["generation"]["hybrid"]["mode"] == "hybrid"
    assert written["generation"]["dense"]["means"]["faithfulness"] == 0.9


def test_write_generation_baseline_refuses_empty_means(tmp_path: Path) -> None:
    destination = tmp_path / "baselines.json"
    report = summarize_report("dense", [_result(budget=True)])
    with pytest.raises(SystemExit, match="no scored cases"):
        write_generation_baseline(report, destination)
    assert not destination.exists()


# --------------------------------------------------------------------------- #
# formatting helpers
# --------------------------------------------------------------------------- #


def test_format_score_none_is_em_dash() -> None:
    assert _format_score(None) == "-"


def test_format_score_rounds_to_three_places() -> None:
    assert _format_score(0.12345) == "0.123"


def test_truncate_leaves_short_text() -> None:
    assert _truncate("short question") == "short question"


def test_truncate_shortens_long_text_with_ellipsis() -> None:
    truncated = _truncate("x" * 80)
    assert truncated.endswith("…")
    assert len(truncated) == 60


# --------------------------------------------------------------------------- #
# run_eval - driven through the real agent graph
# --------------------------------------------------------------------------- #


async def test_run_eval_scores_a_normal_case() -> None:
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
    scorer, metrics = _recording_scorer()
    case = GenerationCase(user_input="How often are boosters needed?", reference="Every 3 years.")

    results = await run_eval(agent, scorer, [case])

    assert len(results) == 1
    assert results[0].budget_exhausted is False
    assert results[0].scores == _scores(0.5, 0.5, 0.5, 0.5)
    faithfulness_call = metrics["faithfulness"].calls[0]
    assert faithfulness_call["retrieved_contexts"] == [passage]
    assert "Every three years [S1]." in faithfulness_call["response"]
    assert metrics["answer_accuracy"].calls[0]["reference"] == "Every 3 years."


async def test_run_eval_skips_and_flags_budget_exhausted() -> None:
    agent = EvalAgent(
        build_test_agent(
            responses=[tool_call_message("retrieve_vet_corpus", "loop")],
            chunks=[make_chunk()],
            settings=make_agent_settings(agent_max_tool_calls=1),
        )
    )
    scorer, metrics = _recording_scorer()
    case = GenerationCase(user_input="Tell me everything.", reference="ref")

    results = await run_eval(agent, scorer, [case])

    assert results[0].budget_exhausted is True
    assert results[0].scores is None
    assert metrics["faithfulness"].calls == []  # the scorer is never called on a canned answer


async def test_run_eval_strips_emergency_banner_before_scoring() -> None:
    agent = EvalAgent(
        build_test_agent(responses=[AIMessage(content=f"Guidance follows. {VET_DISCLAIMER}")])
    )
    scorer, metrics = _recording_scorer()
    case = GenerationCase(
        user_input="My dog is having a seizure, what do I do?", reference="Call your vet now."
    )

    results = await run_eval(agent, scorer, [case])

    assert results[0].emergency is True
    scored_response = metrics["faithfulness"].calls[0]["response"]
    assert not scored_response.startswith(EMERGENCY_BANNER)
    assert "Guidance follows." in scored_response


class _RaisingMetric:
    """A fake metric whose ascore raises, simulating a judge failure (truncated JSON)."""

    async def ascore(self, **kwargs: Any) -> SimpleNamespace:
        raise RuntimeError("judge output truncated")


async def test_run_eval_records_scoring_failure_as_errored() -> None:
    # A judge failure on one case must be recorded and skipped, never crash the run.
    agent = EvalAgent(
        build_test_agent(responses=[AIMessage(content=f"A grounded answer. {VET_DISCLAIMER}")])
    )
    scorer = GenerationScorer(
        faithfulness=_RaisingMetric(),
        answer_accuracy=_RecordingMetric(0.8),
        answer_relevancy=_RecordingMetric(0.7),
        noise_sensitivity=_RecordingMetric(0.1),
    )
    case = GenerationCase(user_input="How often are boosters needed?", reference="Every 3 years.")

    results = await run_eval(agent, scorer, [case])

    assert len(results) == 1
    assert results[0].errored is True
    assert results[0].scores is None
    assert results[0].budget_exhausted is False


async def test_run_eval_records_agent_failure_as_errored() -> None:
    # A crash inside the agent (not the judge) must also be isolated as errored,
    # and the scorer must never be reached for a case whose answer never arrived.
    agent = EvalAgent(build_test_agent(model=RaisingChatModel()))
    scorer, metrics = _recording_scorer()
    case = GenerationCase(user_input="How often are boosters needed?", reference="Every 3 years.")

    results = await run_eval(agent, scorer, [case])

    assert len(results) == 1
    assert results[0].errored is True
    assert results[0].scores is None
    assert results[0].budget_exhausted is False
    assert results[0].emergency is False  # the agent-failure branch forces emergency off
    assert metrics["faithfulness"].calls == []  # scoring is skipped when the agent failed


# --------------------------------------------------------------------------- #
# run_eval - concurrency contract (order preservation + per-case isolation)
# --------------------------------------------------------------------------- #


class _ScriptedEvalAgent:
    """A concurrency-safe fake EvalAgent: each question maps to its own answer.

    build_test_agent's scripted model is a shared response queue, so two cases
    racing on it would be nondeterministic. Keying answers by question lets the
    cases run truly concurrently, which is what pins run_eval's ordering.
    """

    def __init__(self, answers: dict[str, AgentAnswer]) -> None:
        self._answers = answers

    async def answer(self, question: str) -> AgentAnswer:
        return self._answers[question]


class _SelectiveScorer:
    """A fake GenerationScorer that scores every sample except one, which it fails."""

    def __init__(self, scores: GenerationScores, *, fail_on: str) -> None:
        self._scores = scores
        self._fail_on = fail_on

    async def ascore(self, sample: GenerationSample) -> GenerationScores:
        if sample.user_input == self._fail_on:
            raise RuntimeError("judge boom")
        return self._scores


def _agent_answer(text: str, *, contexts: list[str] | None = None) -> AgentAnswer:
    return AgentAnswer(
        text=text,
        citations=[],
        emergency=False,
        tool_calls=[],
        contexts=["Adult dogs need a booster every three years."] if contexts is None else contexts,
    )


async def test_run_eval_preserves_order_across_mixed_outcomes() -> None:
    # run_eval fans cases out concurrently (bounded semaphore + gather): results
    # must come back in input order, and one budget-exhausted or errored case must
    # not stop its siblings from scoring.
    good = GenerationCase(user_input="q-good", reference="ref")
    budget = GenerationCase(user_input="q-budget", reference="ref")
    bad = GenerationCase(user_input="q-bad", reference="ref")
    agent = cast(
        EvalAgent,
        _ScriptedEvalAgent(
            {
                "q-good": _agent_answer(f"A grounded answer [S1]. {VET_DISCLAIMER}"),
                "q-budget": _agent_answer(BUDGET_EXHAUSTED_MESSAGE, contexts=[]),
                "q-bad": _agent_answer(f"Another grounded answer [S1]. {VET_DISCLAIMER}"),
            }
        ),
    )
    scores = _scores(0.9, 0.8, 0.7, 0.1)
    scorer = cast(GenerationScorer, _SelectiveScorer(scores, fail_on="q-bad"))

    results = await run_eval(agent, scorer, [good, budget, bad])

    assert [result.user_input for result in results] == ["q-good", "q-budget", "q-bad"]
    # the good case still scores, despite a budget-exhausted and an errored sibling
    assert results[0].scores == scores
    assert results[0].errored is False
    assert results[0].budget_exhausted is False
    # budget-exhausted case: skipped, not scored, not errored
    assert results[1].budget_exhausted is True
    assert results[1].scores is None
    assert results[1].errored is False
    # failing case: isolated as errored, never crashing the batch
    assert results[2].errored is True
    assert results[2].scores is None
    assert results[2].budget_exhausted is False

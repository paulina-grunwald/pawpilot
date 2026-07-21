"""Tests for the deterministic tool-routing scorer.

run_tool_routing_eval drives the live agent, so the live pass/fail lives in the
opt-in make target. These pin the scoring: acceptable-set matching, micro/macro
F1, the abstention rate, per-bucket accuracy, the golden-set shape, and one
scripted end-to-end run over a fake agent.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from evals.rag.agent_eval import EVAL_DOG_ID, EvalAgent, default_sleep_reader
from evals.rag.tool_routing import (
    ToolGoldenCase,
    load_golden_cases,
    run_tool_routing_eval,
    score_case,
    summarize,
)
from tests.agent.conftest import build_test_agent


def _sleep_case() -> ToolGoldenCase:
    return ToolGoldenCase(
        question="How did she sleep this week?",
        bucket="sleep_or_date",
        acceptable_tool_sets=(
            frozenset({"get_dog_sleep_summary"}),
            frozenset({"get_current_date", "get_dog_sleep_summary"}),
        ),
    )


def _abstain_case() -> ToolGoldenCase:
    return ToolGoldenCase(
        question="What's the weather?",
        bucket="must_abstain",
        acceptable_tool_sets=(frozenset(),),
        must_call_none=True,
    )


# --------------------------------------------------------------------------- #
# case model
# --------------------------------------------------------------------------- #


def test_must_call_none_pins_the_empty_acceptable_set() -> None:
    case = ToolGoldenCase(
        question="q",
        bucket="must_abstain",
        acceptable_tool_sets=(frozenset({"web_search"}),),  # wrong on purpose
        must_call_none=True,
    )
    assert case.acceptable_tool_sets == (frozenset(),)


# --------------------------------------------------------------------------- #
# score_case
# --------------------------------------------------------------------------- #


def test_exact_set_match_is_correct() -> None:
    result = score_case(_sleep_case(), ["get_dog_sleep_summary"])
    assert result.correct
    assert result.false_positive == 0 and result.false_negative == 0


def test_order_and_duplicates_do_not_matter() -> None:
    result = score_case(
        _sleep_case(), ["get_current_date", "get_dog_sleep_summary", "get_current_date"]
    )
    assert result.correct


def test_wrong_tool_is_incorrect_with_fp_and_fn() -> None:
    result = score_case(_sleep_case(), ["lookup_pet_food"])
    assert not result.correct
    assert result.false_positive == 1  # lookup_pet_food not expected
    assert result.false_negative == 1  # get_dog_sleep_summary missing


def test_best_match_picks_the_closest_acceptable_set() -> None:
    # Predicting the two-tool set should match the two-tool gold, not the one-tool one.
    result = score_case(_sleep_case(), ["get_current_date", "get_dog_sleep_summary"])
    assert result.correct
    assert set(result.matched_gold) == {"get_current_date", "get_dog_sleep_summary"}


def test_abstain_case_correct_when_no_tool_ran() -> None:
    result = score_case(_abstain_case(), [])
    assert result.correct
    assert (result.true_positive, result.false_positive, result.false_negative) == (0, 0, 0)


def test_abstain_case_incorrect_when_a_tool_ran() -> None:
    result = score_case(_abstain_case(), ["get_current_date"])
    assert not result.correct
    assert result.false_positive == 1


# --------------------------------------------------------------------------- #
# summarize
# --------------------------------------------------------------------------- #


def test_summarize_computes_accuracy_micro_and_abstention_rate() -> None:
    cases = [_sleep_case(), _sleep_case(), _abstain_case()]
    results = [
        score_case(cases[0], ["get_dog_sleep_summary"]),  # correct
        score_case(cases[1], ["lookup_pet_food"]),  # wrong
        score_case(cases[2], ["web_search"]),  # abstain violated
    ]
    report = summarize(cases, results)
    assert report.total == 3
    assert report.correct == 1
    assert report.exact_set_accuracy == pytest.approx(1 / 3)
    assert report.unnecessary_tool_rate == pytest.approx(1.0)  # the one abstain case called a tool
    assert report.accuracy_by_bucket["sleep_or_date"] == pytest.approx(0.5)
    assert report.accuracy_by_bucket["must_abstain"] == pytest.approx(0.0)
    assert 0.0 <= report.micro_f1 <= 1.0


def test_unnecessary_tool_rate_is_none_without_abstain_cases() -> None:
    case = _sleep_case()
    report = summarize([case], [score_case(case, ["get_dog_sleep_summary"])])
    assert report.unnecessary_tool_rate is None


def test_all_correct_gives_perfect_micro_f1() -> None:
    cases = [_sleep_case(), _abstain_case()]
    results = [score_case(cases[0], ["get_dog_sleep_summary"]), score_case(cases[1], [])]
    report = summarize(cases, results)
    assert report.exact_set_accuracy == pytest.approx(1.0)
    assert report.micro_f1 == pytest.approx(1.0)
    assert report.mean_tool_calls_per_query == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# golden set
# --------------------------------------------------------------------------- #


def test_golden_set_loads_and_covers_three_buckets() -> None:
    cases = load_golden_cases()
    assert len(cases) >= 18
    assert {case.bucket for case in cases} == {"sleep_or_date", "named_food", "must_abstain"}


def test_golden_abstain_cases_are_all_must_call_none() -> None:
    cases = load_golden_cases()
    for case in cases:
        if case.bucket == "must_abstain":
            assert case.must_call_none
            assert case.acceptable_tool_sets == (frozenset(),)


# --------------------------------------------------------------------------- #
# end-to-end over a scripted agent
# --------------------------------------------------------------------------- #


def _sleep_tool_call() -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "get_dog_sleep_summary", "args": {"days": 7}, "id": "s1", "type": "tool_call"}
        ],
    )


@pytest.mark.asyncio
async def test_end_to_end_scores_a_correct_sleep_route() -> None:
    agent = build_test_agent(
        responses=[_sleep_tool_call(), AIMessage(content="She slept about 9 hours a night.")],
        with_memory=True,
    )
    eval_agent = EvalAgent(agent, dog_id=EVAL_DOG_ID, sleep_reader=default_sleep_reader())
    report = await run_tool_routing_eval(eval_agent, [_sleep_case()], concurrency=1)
    assert report.correct == 1
    assert report.results[0].invoked_tools == ("get_dog_sleep_summary",)

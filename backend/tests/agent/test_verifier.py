"""Tests for the deterministic post-answer verifier."""

from __future__ import annotations

from app.agent.prompt import OFF_TOPIC_MESSAGE, SYSTEM_PROMPT
from app.agent.verifier import verify_answer

_CITEABLE_TOOLS = ["retrieve_vet_corpus"]
_LONG_ANSWER = "Occasional grass eating is usually fine. " * 8  # > 200 chars, no citation


def test_clean_cited_answer_passes() -> None:
    result = verify_answer(
        answer_text="Grass eating is usually benign [S1]. " + "More detail. " * 20,
        tool_calls=_CITEABLE_TOOLS,
        has_citations=True,
        system_prompt=SYSTEM_PROMPT,
    )
    assert result.ok
    assert result.flags == ()


def test_retrieval_ran_but_nothing_cited_is_flagged() -> None:
    result = verify_answer(
        answer_text=_LONG_ANSWER,
        tool_calls=_CITEABLE_TOOLS,
        has_citations=False,
        system_prompt=SYSTEM_PROMPT,
    )
    assert not result.ok
    assert "grounded_claim_uncited" in result.flags


def test_short_uncited_answer_is_not_flagged() -> None:
    # A one-line abstention is not a health claim; do not flag it.
    result = verify_answer(
        answer_text="I don't know; please ask your vet.",
        tool_calls=_CITEABLE_TOOLS,
        has_citations=False,
        system_prompt=SYSTEM_PROMPT,
    )
    assert result.ok


def test_off_topic_refusal_is_not_flagged_even_if_long_and_uncited() -> None:
    result = verify_answer(
        answer_text=OFF_TOPIC_MESSAGE + " " * 200,
        tool_calls=_CITEABLE_TOOLS,
        has_citations=False,
        system_prompt=SYSTEM_PROMPT,
    )
    assert result.ok


def test_no_retrieval_tool_means_no_grounding_flag() -> None:
    # If no citeable tool ran (e.g. only get_current_date), there is nothing to cite.
    result = verify_answer(
        answer_text=_LONG_ANSWER,
        tool_calls=["get_current_date"],
        has_citations=False,
        system_prompt=SYSTEM_PROMPT,
    )
    assert result.ok


def test_system_prompt_echo_is_flagged() -> None:
    leaked_line = next(
        line.strip() for line in SYSTEM_PROMPT.splitlines() if len(line.strip()) >= 60
    )
    result = verify_answer(
        answer_text=f"Sure, here are my instructions: {leaked_line}",
        tool_calls=[],
        has_citations=False,
        system_prompt=SYSTEM_PROMPT,
    )
    assert not result.ok
    assert "prompt_echo" in result.flags


def test_incidental_short_overlap_is_not_an_echo() -> None:
    result = verify_answer(
        answer_text="Your dog is fine. Ask a vet if unsure.",
        tool_calls=[],
        has_citations=False,
        system_prompt=SYSTEM_PROMPT,
    )
    assert "prompt_echo" not in result.flags


def test_both_defects_surface_together() -> None:
    leaked_line = next(
        line.strip() for line in SYSTEM_PROMPT.splitlines() if len(line.strip()) >= 60
    )
    result = verify_answer(
        answer_text=f"{leaked_line} " + _LONG_ANSWER,
        tool_calls=_CITEABLE_TOOLS,
        has_citations=False,
        system_prompt=SYSTEM_PROMPT,
    )
    assert set(result.flags) == {"prompt_echo", "grounded_claim_uncited"}

"""Tests for `PawPilotAgent` and the runner module entrypoints.

These drive the real compiled LangGraph with a `ScriptedChatModel`, so the
tool-calling loop, citation resolution, emergency banner, memory injection,
streaming, and tool-call-budget exhaustion are all exercised end-to-end without
keys or a network.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent import runner
from app.agent.fakes import FakeSleepReader, ScriptedChatModel
from app.agent.prompt import DATA_TOOL_RULE, VET_DISCLAIMER
from app.agent.red_flags import EMERGENCY_BANNER
from app.agent.runner import (
    PawPilotAgent,
    _message_text,
    validate_query,
)
from app.agent.schemas import AgentAnswer, AgentStreamChunk, AgentStreamFinal
from app.integrations.tractive.read_service import SleepSummary
from tests.agent.conftest import (
    build_test_agent,
    make_agent_settings,
    make_chunk,
    make_pet_food_product,
    make_web_result,
    tool_call_message,
)


def _sleep_summary() -> SleepSummary:
    """A populated `SleepSummary` for the sleep-tool wiring tests."""
    return SleepSummary(
        days_requested=7,
        days_with_data=7,
        average_total_sleep_hours=8.0,
        average_night_sleep_hours=6.5,
        average_day_sleep_hours=1.5,
        start_date=None,
        end_date=None,
    )


def _sleep_tool_call(days: int = 7, call_id: str = "call-1") -> AIMessage:
    """An assistant turn that calls the sleep tool with a ``days`` argument."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_dog_sleep_summary",
                "args": {"days": days},
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def _current_date_tool_call(call_id: str = "call-1") -> AIMessage:
    """An assistant turn that calls the always-on clock tool (no arguments)."""
    return AIMessage(
        content="",
        tool_calls=[{"name": "get_current_date", "args": {}, "id": call_id, "type": "tool_call"}],
    )


# --------------------------------------------------------------------------- #
# validate_query
# --------------------------------------------------------------------------- #


def test_validate_query_accepts_normal_text() -> None:
    validate_query("Is kibble ok for my Aussie?")


@pytest.mark.parametrize("query", ["", "   ", "\n\t "])
def test_validate_query_rejects_blank(query: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        validate_query(query)


def test_validate_query_rejects_oversize() -> None:
    with pytest.raises(ValueError, match="at most 2000"):
        validate_query("x" * 2001)


def test_validate_query_accepts_exactly_max_length() -> None:
    validate_query("x" * 2000)


# --------------------------------------------------------------------------- #
# _message_text
# --------------------------------------------------------------------------- #


def test_message_text_from_plain_string() -> None:
    assert _message_text(AIMessage(content="hello")) == "hello"


def test_message_text_from_content_blocks() -> None:
    message = AIMessage(
        content=[
            {"type": "text", "text": "part one "},
            {"type": "text", "text": "part two"},
            {"type": "image", "url": "ignored"},
        ]
    )
    assert _message_text(message) == "part one part two"


def test_message_text_from_string_blocks() -> None:
    message = AIMessage(content=["a", "b"])
    assert _message_text(message) == "ab"


# --------------------------------------------------------------------------- #
# run / arun — happy paths
# --------------------------------------------------------------------------- #


def test_run_answers_without_tools() -> None:
    agent = build_test_agent(responses=[AIMessage(content=f"Feed twice daily. {VET_DISCLAIMER}")])
    answer = agent.run("How often should I feed my dog?")
    assert isinstance(answer, AgentAnswer)
    assert "Feed twice daily." in answer.text
    assert answer.tool_calls == []
    assert answer.citations == []
    assert answer.emergency is False


def test_run_resolves_corpus_citation_after_tool_call() -> None:
    agent = build_test_agent(
        responses=[
            tool_call_message("retrieve_vet_corpus", "vaccine booster"),
            AIMessage(content=f"Boost every three years [S1]. {VET_DISCLAIMER}"),
        ],
        chunks=[make_chunk()],
    )
    answer = agent.run("How often are boosters needed?")
    assert answer.tool_calls == ["retrieve_vet_corpus"]
    assert [citation.ref for citation in answer.citations] == ["S1"]
    assert answer.citations[0].kind == "corpus"
    assert answer.citations[0].title == "WSAVA Vaccination Guidelines"


def test_run_ignores_unreferenced_passages() -> None:
    agent = build_test_agent(
        responses=[
            tool_call_message("retrieve_vet_corpus", "diet"),
            AIMessage(content="A general answer with no citation ids."),
        ],
        chunks=[make_chunk(), make_chunk(chunk_id="chunk-2")],
    )
    answer = agent.run("What should my dog eat?")
    assert answer.citations == []


async def test_arun_resolves_web_citation() -> None:
    agent = build_test_agent(
        responses=[
            tool_call_message("web_search", "brand x recall"),
            AIMessage(content=f"There was a recall [W1]. {VET_DISCLAIMER}"),
        ],
        web_results=[make_web_result()],
    )
    answer = await agent.arun("Any recalls for brand X?")
    assert answer.tool_calls == ["web_search"]
    assert [citation.ref for citation in answer.citations] == ["W1"]
    assert answer.citations[0].kind == "web"


def test_run_resolves_pet_food_citation() -> None:
    agent = build_test_agent(
        responses=[
            tool_call_message("lookup_pet_food", "orijen six fish"),
            AIMessage(content=f"It is 40% crude protein [F1]. {VET_DISCLAIMER}"),
        ],
        pet_food_products=[make_pet_food_product()],
    )
    answer = agent.run("What are the macros in Orijen Six Fish?")
    assert answer.tool_calls == ["lookup_pet_food"]
    assert [citation.ref for citation in answer.citations] == ["F1"]
    assert answer.citations[0].kind == "food"
    assert answer.citations[0].title == "Orijen Six Fish"


# --------------------------------------------------------------------------- #
# Emergency banner
# --------------------------------------------------------------------------- #


def test_run_prepends_emergency_banner_for_red_flag() -> None:
    agent = build_test_agent(responses=[AIMessage(content="Please see guidance below.")])
    answer = agent.run("My dog is having a seizure, what do I do?")
    assert answer.emergency is True
    assert answer.text.startswith(EMERGENCY_BANNER)


def test_run_no_banner_for_ordinary_question() -> None:
    agent = build_test_agent(responses=[AIMessage(content="All good.")])
    answer = agent.run("What is a good treat for training?")
    assert answer.emergency is False
    assert not answer.text.startswith(EMERGENCY_BANNER)


# --------------------------------------------------------------------------- #
# Tool-call budget exhaustion
# --------------------------------------------------------------------------- #


def test_run_returns_budget_message_when_loop_never_terminates() -> None:
    # A model that only ever calls a tool never produces a final answer, so the
    # graph exhausts its recursion limit.
    agent = build_test_agent(
        responses=[tool_call_message("retrieve_vet_corpus", "loop")],
        chunks=[make_chunk()],
        settings=make_agent_settings(agent_max_tool_calls=1),
    )
    answer = agent.run("Tell me everything.")
    assert "couldn't finish researching" in answer.text
    assert answer.citations == []


async def test_arun_returns_budget_message_when_loop_never_terminates() -> None:
    agent = build_test_agent(
        responses=[tool_call_message("web_search", "loop")],
        web_results=[make_web_result()],
        settings=make_agent_settings(agent_max_tool_calls=1),
    )
    answer = await agent.arun("Tell me everything.")
    assert "couldn't finish researching" in answer.text


def test_run_allows_exactly_the_budgeted_number_of_tool_calls() -> None:
    # With a budget of 2, a run that makes exactly 2 tool calls then answers must
    # succeed — this pins the off-by-one in tool_call_budget_to_recursion_limit.
    agent = build_test_agent(
        responses=[
            tool_call_message("retrieve_vet_corpus", "first"),
            tool_call_message("retrieve_vet_corpus", "second"),
            AIMessage(content=f"Answer after two lookups [S1]. {VET_DISCLAIMER}"),
        ],
        chunks=[make_chunk(), make_chunk(chunk_id="chunk-2")],
        settings=make_agent_settings(agent_max_tool_calls=2),
    )
    answer = agent.run("Two-step question")
    assert "couldn't finish researching" not in answer.text
    assert "Answer after two lookups" in answer.text
    assert answer.tool_calls == ["retrieve_vet_corpus", "retrieve_vet_corpus"]


def test_run_exhausts_when_tool_calls_exceed_the_budget_by_one() -> None:
    # One more tool call than the budget allows tips the run over its recursion
    # limit, so it returns the budget-exhausted message instead of the answer.
    agent = build_test_agent(
        responses=[
            tool_call_message("retrieve_vet_corpus", "first"),
            tool_call_message("retrieve_vet_corpus", "second"),
            tool_call_message("retrieve_vet_corpus", "third"),
            AIMessage(content=f"Never reached. {VET_DISCLAIMER}"),
        ],
        chunks=[make_chunk(), make_chunk(chunk_id="chunk-2"), make_chunk(chunk_id="chunk-3")],
        settings=make_agent_settings(agent_max_tool_calls=2),
    )
    answer = agent.run("Three-step question")
    assert "couldn't finish researching" in answer.text


# --------------------------------------------------------------------------- #
# Memory injection into the system prompt
# --------------------------------------------------------------------------- #


async def test_arun_injects_remembered_facts_into_system_prompt() -> None:
    model = ScriptedChatModel(responses=[AIMessage(content=f"Noted. {VET_DISCLAIMER}")])
    agent = build_test_agent(model=model, with_memory=True)
    assert agent.memory_store is not None
    await agent.memory_store.asave("dog-1", "breed", "Australian Shepherd")

    await agent.arun("What breed care tips apply?", dog_id="dog-1")

    system_messages = [
        message.content
        for batch in model.received_batches
        for message in batch
        if message.type == "system"
    ]
    assert any("Australian Shepherd" in str(content) for content in system_messages)


async def test_arun_without_dog_id_has_no_memory_block() -> None:
    model = ScriptedChatModel(responses=[AIMessage(content=f"Sure. {VET_DISCLAIMER}")])
    agent = build_test_agent(model=model, with_memory=True)
    assert agent.memory_store is not None
    await agent.memory_store.asave("dog-1", "breed", "Australian Shepherd")

    await agent.arun("General question")

    system_messages = [
        str(message.content)
        for batch in model.received_batches
        for message in batch
        if message.type == "system"
    ]
    assert all("Australian Shepherd" not in content for content in system_messages)


def test_memory_context_inactive_without_store() -> None:
    agent = build_test_agent(responses=[AIMessage(content="hi")])
    active, block = agent._memory_context("dog-1")
    assert active is False
    assert block == ""


# --------------------------------------------------------------------------- #
# Sleep tool wiring (get_dog_sleep_summary)
# --------------------------------------------------------------------------- #


async def test_arun_invokes_sleep_tool_when_reader_supplied() -> None:
    reader = FakeSleepReader(_sleep_summary())
    agent = build_test_agent(
        responses=[
            _sleep_tool_call(days=7),
            AIMessage(content=f"Your dog slept about 8 hours a night. {VET_DISCLAIMER}"),
        ],
    )

    answer = await agent.arun("How much did my dog sleep this week?", sleep_reader=reader)

    assert answer.tool_calls == ["get_dog_sleep_summary"]
    assert reader.requested_days == [7]
    assert "8 hours" in answer.text


async def test_arun_without_reader_does_not_wire_sleep_tool() -> None:
    model = ScriptedChatModel(responses=[AIMessage(content=f"Sure. {VET_DISCLAIMER}")])
    agent = build_test_agent(model=model)

    await agent.arun("General question")

    system_messages = [
        str(message.content)
        for batch in model.received_batches
        for message in batch
        if message.type == "system"
    ]
    assert all(DATA_TOOL_RULE not in content for content in system_messages)


async def test_arun_includes_data_rule_in_system_prompt_when_reader_supplied() -> None:
    model = ScriptedChatModel(responses=[AIMessage(content=f"Sure. {VET_DISCLAIMER}")])
    agent = build_test_agent(model=model)

    await agent.arun("General question", sleep_reader=FakeSleepReader(_sleep_summary()))

    system_messages = [
        str(message.content)
        for batch in model.received_batches
        for message in batch
        if message.type == "system"
    ]
    assert any(DATA_TOOL_RULE in content for content in system_messages)


async def test_astream_run_invokes_sleep_tool_when_reader_supplied() -> None:
    reader = FakeSleepReader(_sleep_summary())
    agent = build_test_agent(
        responses=[
            _sleep_tool_call(days=7),
            AIMessage(content=f"About 8 hours a night. {VET_DISCLAIMER}"),
        ],
    )

    events = [event async for event in agent.astream_run("How much sleep?", sleep_reader=reader)]

    finals = [event for event in events if isinstance(event, AgentStreamFinal)]
    assert len(finals) == 1
    assert finals[0].tool_calls == ["get_dog_sleep_summary"]
    assert reader.requested_days == [7]


# --------------------------------------------------------------------------- #
# Clock tool wiring (get_current_date) — always on, no reader required
# --------------------------------------------------------------------------- #


def test_run_invokes_clock_tool_without_reader_or_memory() -> None:
    agent = build_test_agent(
        responses=[
            _current_date_tool_call(),
            AIMessage(content=f"Today is noted. {VET_DISCLAIMER}"),
        ],
    )

    answer = agent.run("What is today's date?")

    assert answer.tool_calls == ["get_current_date"]
    assert "Today is noted." in answer.text


async def test_arun_resolves_dated_sleep_via_clock_then_sleep_tool() -> None:
    reader = FakeSleepReader(_sleep_summary())
    agent = build_test_agent(
        responses=[
            _current_date_tool_call(),
            _sleep_tool_call(days=7),
            AIMessage(content=f"About 8 hours a night. {VET_DISCLAIMER}"),
        ],
    )

    answer = await agent.arun("How much did my dog sleep last Tuesday?", sleep_reader=reader)

    assert answer.tool_calls == ["get_current_date", "get_dog_sleep_summary"]


# --------------------------------------------------------------------------- #
# Streaming
# --------------------------------------------------------------------------- #


async def test_astream_run_yields_tokens_then_final() -> None:
    agent = build_test_agent(
        responses=[
            tool_call_message("retrieve_vet_corpus", "vaccines"),
            AIMessage(content=f"Every three years [S1]. {VET_DISCLAIMER}"),
        ],
        chunks=[make_chunk()],
    )
    events = [event async for event in agent.astream_run("How often?")]
    chunks = [event for event in events if isinstance(event, AgentStreamChunk)]
    finals = [event for event in events if isinstance(event, AgentStreamFinal)]
    assert len(finals) == 1
    assert finals[0].tool_calls == ["retrieve_vet_corpus"]
    assert [citation.ref for citation in finals[0].citations] == ["S1"]
    streamed = "".join(chunk.text for chunk in chunks)
    assert "Every three years [S1]." in streamed


async def test_astream_run_emits_emergency_banner_first() -> None:
    agent = build_test_agent(responses=[AIMessage(content="Guidance follows.")])
    events = [event async for event in agent.astream_run("My dog collapsed suddenly")]
    assert isinstance(events[0], AgentStreamChunk)
    assert events[0].text == EMERGENCY_BANNER
    final = events[-1]
    assert isinstance(final, AgentStreamFinal)
    assert final.emergency is True


async def test_astream_run_budget_exhaustion_streams_message_and_final() -> None:
    agent = build_test_agent(
        responses=[tool_call_message("retrieve_vet_corpus", "loop")],
        chunks=[make_chunk()],
        settings=make_agent_settings(agent_max_tool_calls=1),
    )
    events = [event async for event in agent.astream_run("loop please")]
    text = "".join(event.text for event in events if isinstance(event, AgentStreamChunk))
    assert "couldn't finish researching" in text
    assert isinstance(events[-1], AgentStreamFinal)


# --------------------------------------------------------------------------- #
# Short-term memory (checkpointer) continuity
# --------------------------------------------------------------------------- #


async def test_thread_history_is_restored_across_turns() -> None:
    model = ScriptedChatModel(
        responses=[
            AIMessage(content=f"First answer. {VET_DISCLAIMER}"),
            AIMessage(content=f"Second answer. {VET_DISCLAIMER}"),
        ]
    )
    agent = build_test_agent(model=model, with_thread=True)
    await agent.arun("First question", thread_id="thread-a")
    await agent.arun("Second question", thread_id="thread-a")

    last_batch = model.received_batches[-1]
    human_texts = [
        str(message.content) for message in last_batch if isinstance(message, HumanMessage)
    ]
    assert "First question" in human_texts
    assert "Second question" in human_texts


# --------------------------------------------------------------------------- #
# Module-level singleton helpers
# --------------------------------------------------------------------------- #


def test_set_and_get_default_agent() -> None:
    agent = build_test_agent(responses=[AIMessage(content="hi")])
    try:
        runner.set_default_agent(agent)
        assert runner.get_default_agent() is agent
    finally:
        runner.clear_default_agent()


def test_active_memory_store_tracks_default_agent() -> None:
    agent = build_test_agent(responses=[AIMessage(content="hi")], with_memory=True)
    try:
        runner.set_default_agent(agent)
        assert runner.active_memory_store() is agent.memory_store
    finally:
        runner.clear_default_agent()


def test_active_memory_store_none_when_no_default_agent() -> None:
    runner.clear_default_agent()
    assert runner.active_memory_store() is None


def test_get_default_agent_lazily_builds_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = build_test_agent(responses=[AIMessage(content="hi")])
    build_calls = 0

    def fake_build() -> PawPilotAgent:
        nonlocal build_calls
        build_calls += 1
        return agent

    monkeypatch.setattr(runner, "_build_in_memory_agent", fake_build)
    runner.clear_default_agent()
    try:
        assert runner.get_default_agent() is agent
        assert runner.get_default_agent() is agent
        assert build_calls == 1
    finally:
        runner.clear_default_agent()


def test_run_agent_module_helper_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = build_test_agent(responses=[AIMessage(content=f"Answer. {VET_DISCLAIMER}")])
    monkeypatch.setattr(runner, "_build_in_memory_agent", lambda: agent)
    runner.clear_default_agent()
    try:
        answer = runner.run_agent("A question")
        assert "Answer." in answer.text
    finally:
        runner.clear_default_agent()


async def test_arun_agent_module_helper_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    agent = build_test_agent(responses=[AIMessage(content=f"Async answer. {VET_DISCLAIMER}")])
    monkeypatch.setattr(runner, "_build_in_memory_agent", lambda: agent)
    runner.clear_default_agent()
    try:
        answer = await runner.arun_agent("A question")
        assert "Async answer." in answer.text
    finally:
        runner.clear_default_agent()

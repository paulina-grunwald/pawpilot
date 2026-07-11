"""Tests for the chat-model builder, graph compilation, and budget arithmetic.

`app.agent.graph` is pure wiring: it constructs a `ChatOpenAI` from settings,
compiles the prebuilt ReAct agent, and converts a tool-call budget into a
recursion limit. These tests exercise each piece with the network-free doubles
from ``app.agent.fakes`` plus a `StubRetriever`, so nothing here needs a key,
Postgres, or a live gateway.
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any, cast

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import SecretStr

from app.agent.citations import CitationRegistry
from app.agent.fakes import FakeWebSearch, ScriptedChatModel
from app.agent.graph import (
    build_agent_graph,
    build_chat_model,
    tool_call_budget_to_recursion_limit,
)
from app.agent.tools import build_agent_tools
from app.agent.web_search import WebSearchResult
from app.rag.retriever import VetCorpusRetriever
from app.rag.schemas import RetrievedChunk
from tests.agent.conftest import (
    StubRetriever,
    make_agent_settings,
    make_chunk,
    tool_call_message,
)

# --------------------------------------------------------------------------- #
# Local helpers
# --------------------------------------------------------------------------- #


def build_scripted_graph(
    responses: list[AIMessage],
    *,
    chunks: list[RetrievedChunk] | None = None,
    web_results: list[WebSearchResult] | None = None,
    system_prompt: str | None = None,
    checkpointer: InMemorySaver | None = None,
    top_k: int = 3,
) -> tuple[Any, ScriptedChatModel, list[str]]:
    """Compile a graph over a `ScriptedChatModel` and the network-free tools.

    Returns the compiled graph, the model (so tests can inspect
    ``received_batches``), and the ``invoked_tools`` list the tools append to.
    """
    registry = CitationRegistry()
    invoked_tools: list[str] = []
    tools = build_agent_tools(
        cast(VetCorpusRetriever, StubRetriever(chunks)),
        FakeWebSearch(web_results),
        registry,
        invoked_tools,
        top_k=top_k,
    )
    model = ScriptedChatModel(responses=responses)
    graph = build_agent_graph(
        model,
        tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )
    return graph, model, invoked_tools


def last_message_text(result: object) -> str:
    """Pull the final message's text out of a graph invoke result."""
    messages = cast("dict[str, list[AIMessage]]", result)["messages"]
    return str(messages[-1].content)


# --------------------------------------------------------------------------- #
# tool_call_budget_to_recursion_limit
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("max_tool_calls", "expected_limit"),
    [(1, 4), (6, 14), (20, 42)],
)
def test_tool_call_budget_to_recursion_limit_known_values(
    max_tool_calls: int, expected_limit: int
) -> None:
    assert tool_call_budget_to_recursion_limit(max_tool_calls) == expected_limit


@pytest.mark.parametrize("max_tool_calls", [1, 2, 3, 7, 11, 20])
def test_tool_call_budget_to_recursion_limit_matches_formula(max_tool_calls: int) -> None:
    assert tool_call_budget_to_recursion_limit(max_tool_calls) == 2 * max_tool_calls + 2


def test_tool_call_budget_to_recursion_limit_is_monotonic() -> None:
    limits = [tool_call_budget_to_recursion_limit(count) for count in range(1, 10)]
    for lower, higher in pairwise(limits):
        assert higher == lower + 2


# --------------------------------------------------------------------------- #
# build_chat_model
# --------------------------------------------------------------------------- #


def test_build_chat_model_returns_chat_openai() -> None:
    model = build_chat_model(make_agent_settings())
    assert isinstance(model, ChatOpenAI)


def test_build_chat_model_uses_settings_model_and_temperature() -> None:
    settings = make_agent_settings(agent_model="openai/gpt-x", agent_temperature=0.3)
    model = build_chat_model(settings)
    assert model.model_name == "openai/gpt-x"
    assert model.temperature == 0.3


def test_build_chat_model_defaults_track_settings_defaults() -> None:
    settings = make_agent_settings()
    model = build_chat_model(settings)
    assert model.model_name == settings.agent_model
    assert model.temperature == settings.agent_temperature


def test_build_chat_model_points_at_gateway_base_url() -> None:
    settings = make_agent_settings()
    model = build_chat_model(settings)
    assert model.openai_api_base == settings.gateway_base_url


def test_build_chat_model_carries_the_gateway_api_key() -> None:
    settings = make_agent_settings()
    model = build_chat_model(settings)
    api_key = model.openai_api_key
    assert isinstance(api_key, SecretStr)
    assert api_key.get_secret_value() == settings.gateway_api_key.get_secret_value()


def test_build_chat_model_returns_a_chat_openai_instance() -> None:
    # Construction builds a real ChatOpenAI (client is created lazily, so this
    # needs no key or network); invocation is never exercised here.
    model = build_chat_model(make_agent_settings())
    assert isinstance(model, ChatOpenAI)


# --------------------------------------------------------------------------- #
# build_agent_graph — compilation and invocation
# --------------------------------------------------------------------------- #


def test_build_agent_graph_returns_something_invocable() -> None:
    graph, _model, _invoked = build_scripted_graph([AIMessage(content="hello")])
    assert hasattr(graph, "invoke")
    assert callable(graph.invoke)


def test_build_agent_graph_returns_final_answer_without_tools() -> None:
    graph, _model, invoked_tools = build_scripted_graph([AIMessage(content="Feed twice daily.")])
    result = graph.invoke({"messages": [HumanMessage("hi")]})
    assert last_message_text(result) == "Feed twice daily."
    assert invoked_tools == []


def test_build_agent_graph_drives_the_corpus_tool_then_answers() -> None:
    graph, _model, invoked_tools = build_scripted_graph(
        [
            tool_call_message("retrieve_vet_corpus", "vaccine booster"),
            AIMessage(content="Answer after corpus."),
        ],
        chunks=[make_chunk()],
    )
    result = graph.invoke({"messages": [HumanMessage("How often?")]})
    assert invoked_tools == ["retrieve_vet_corpus"]
    assert last_message_text(result) == "Answer after corpus."


def test_build_agent_graph_drives_the_web_tool_then_answers() -> None:
    graph, _model, invoked_tools = build_scripted_graph(
        [
            tool_call_message("web_search", "brand x recall"),
            AIMessage(content="Answer after web."),
        ],
        web_results=[],
    )
    result = graph.invoke({"messages": [HumanMessage("Any recalls?")]})
    assert invoked_tools == ["web_search"]
    assert last_message_text(result) == "Answer after web."


def test_build_agent_graph_applies_the_system_prompt_on_every_model_call() -> None:
    graph, model, _invoked = build_scripted_graph(
        [AIMessage(content="ok")],
        system_prompt="You are a vet helper SENTINEL.",
    )
    graph.invoke({"messages": [HumanMessage("hi")]})
    system_texts = [
        str(message.content)
        for batch in model.received_batches
        for message in batch
        if isinstance(message, SystemMessage)
    ]
    assert any("SENTINEL" in text for text in system_texts)


def test_build_agent_graph_without_system_prompt_sends_no_system_message() -> None:
    graph, model, _invoked = build_scripted_graph([AIMessage(content="ok")])
    graph.invoke({"messages": [HumanMessage("hi")]})
    system_messages = [
        message
        for batch in model.received_batches
        for message in batch
        if isinstance(message, SystemMessage)
    ]
    assert system_messages == []


def test_build_agent_graph_checkpointer_restores_history_across_turns() -> None:
    graph, model, _invoked = build_scripted_graph(
        [AIMessage(content="First answer."), AIMessage(content="Second answer.")],
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "thread-a"}}
    graph.invoke({"messages": [HumanMessage("First question")]}, config=config)
    graph.invoke({"messages": [HumanMessage("Second question")]}, config=config)

    last_batch = model.received_batches[-1]
    human_texts = [
        str(message.content) for message in last_batch if isinstance(message, HumanMessage)
    ]
    assert "First question" in human_texts
    assert "Second question" in human_texts


def test_build_agent_graph_without_checkpointer_forgets_between_runs() -> None:
    graph, model, _invoked = build_scripted_graph(
        [AIMessage(content="First answer."), AIMessage(content="Second answer.")]
    )
    graph.invoke({"messages": [HumanMessage("First question")]})
    graph.invoke({"messages": [HumanMessage("Second question")]})

    last_batch = model.received_batches[-1]
    human_texts = [
        str(message.content) for message in last_batch if isinstance(message, HumanMessage)
    ]
    assert "First question" not in human_texts
    assert "Second question" in human_texts

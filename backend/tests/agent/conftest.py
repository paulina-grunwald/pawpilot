"""Shared fixtures and test doubles for the Ask PawPilot agent suite.

Everything here is network-free: a `StubRetriever` that replays canned corpus
chunks, the `ScriptedChatModel`/`FakeWebSearch` doubles from ``app.agent.fakes``,
and an in-memory checkpointer + store. `build_test_agent` wires them into a real
`PawPilotAgent` so tests exercise the genuine graph without keys or a network.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from typing import Any, cast

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from langchain_core.runnables import Runnable
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from pydantic import SecretStr

from app.agent.config import AgentSettings
from app.agent.fakes import FakePetFood, FakeWebSearch, ScriptedChatModel
from app.agent.memory import DogMemoryStore
from app.agent.pet_food import PetFoodNutrient, PetFoodProduct
from app.agent.runner import PawPilotAgent
from app.agent.web_search import WebSearchResult
from app.rag.retriever import VetCorpusRetriever
from app.rag.schemas import RetrievalMode, RetrievedChunk, SourceTier


class StubRetriever:
    """A retriever that returns preset chunks and never touches Qdrant.

    Duck-typed rather than subclassed: the parent's ``retrieve`` is wrapped by
    ``@traceable`` (which rewrites its signature), so composition + a ``cast`` at
    the call site is cleaner than fighting the override check.
    """

    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self._chunks = list(chunks) if chunks is not None else []

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        sources: list[str] | None = None,
        source_tiers: list[SourceTier] | None = None,
        mode: RetrievalMode = "dense",
    ) -> list[RetrievedChunk]:
        if top_k is None:
            return list(self._chunks)
        return list(self._chunks[:top_k])


class RaisingChatModel(BaseChatModel):
    """A chat model that raises on every generation — drives the failure paths."""

    @property
    def _llm_type(self) -> str:
        return "raising-fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise RuntimeError("model boom")

    def bind_tools(  # type: ignore[override]  # test double: binding is a no-op
        self, tools: Sequence[Any], **kwargs: Any
    ) -> Runnable[Any, BaseMessage]:
        return self


def make_agent_settings(**overrides: object) -> AgentSettings:
    """An `AgentSettings` with a dummy key, ignoring any real ``.env`` on disk."""
    values: dict[str, object] = {"gateway_api_key": SecretStr("test-gateway-key")}
    values.update(overrides)
    return AgentSettings(_env_file=None, **values)  # type: ignore[call-arg, arg-type]


def make_chunk(**overrides: object) -> RetrievedChunk:
    """A fully-populated `RetrievedChunk` for citation and retrieval tests."""
    values: dict[str, object] = {
        "chunk_id": "chunk-1",
        "text": "Adult dogs need a core booster every three years.",
        "score": 0.91,
        "source_id": "wsava-2024",
        "title": "WSAVA Vaccination Guidelines",
        "organization": "WSAVA",
        "year": 2024,
        "url": "https://example.org/wsava.pdf",
        "section": "Core vaccines",
        "page_start": 12,
        "page_end": 13,
        "source_tier": "guideline",
    }
    values.update(overrides)
    return RetrievedChunk.model_validate(values)


def make_web_result(**overrides: object) -> WebSearchResult:
    """A `WebSearchResult` for web-search and citation tests."""
    values: dict[str, object] = {
        "title": "Brand X kibble recall",
        "url": "https://news.example.com/recall",
        "content": "The manufacturer recalled several lots this week.",
    }
    values.update(overrides)
    return WebSearchResult.model_validate(values)


def make_pet_food_product(**overrides: object) -> PetFoodProduct:
    """A fully-populated `PetFoodProduct` for pet-food and citation tests."""
    values: dict[str, object] = {
        "code": "0064992281182",
        "name": "Six Fish",
        "brands": "Orijen",
        "quantity": "1.8 kg",
        "ingredients_text": "Whole sardine, whole hake, whole mackerel.",
        "nutrients": [
            PetFoodNutrient(label="Crude protein", value=40.0),
            PetFoodNutrient(label="Crude fat", value=19.0),
            PetFoodNutrient(label="Crude fibre", value=3.0),
        ],
        "url": "https://world.openpetfoodfacts.org/product/0064992281182",
    }
    values.update(overrides)
    return PetFoodProduct.model_validate(values)


def tool_call_message(name: str, query: str, call_id: str = "call-1") -> AIMessage:
    """An assistant turn that calls ``name`` with a ``query`` argument."""
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": {"query": query}, "id": call_id, "type": "tool_call"}],
    )


def build_test_agent(
    *,
    responses: list[AIMessage] | None = None,
    model: BaseChatModel | None = None,
    chunks: list[RetrievedChunk] | None = None,
    web_results: list[WebSearchResult] | None = None,
    pet_food_products: list[PetFoodProduct] | None = None,
    with_memory: bool = False,
    with_thread: bool = False,
    max_memories: int = 20,
    settings: AgentSettings | None = None,
) -> PawPilotAgent:
    """Assemble a `PawPilotAgent` from the in-memory doubles.

    Pass ``model`` to inject a `ScriptedChatModel` you hold a reference to (so you
    can inspect ``received_batches``); otherwise ``responses`` builds one.
    """
    resolved_settings = settings if settings is not None else make_agent_settings()
    resolved_model = model if model is not None else ScriptedChatModel(responses=responses or [])
    memory_store = (
        DogMemoryStore(InMemoryStore(), max_memories=max_memories) if with_memory else None
    )
    return PawPilotAgent(
        model=resolved_model,
        retriever=cast(VetCorpusRetriever, StubRetriever(chunks)),
        web_search=FakeWebSearch(web_results),
        pet_food=FakePetFood(pet_food_products),
        settings=resolved_settings,
        checkpointer=InMemorySaver() if with_thread else None,
        memory_store=memory_store,
    )


@pytest.fixture
def install_agent() -> Iterator[Callable[[PawPilotAgent], None]]:
    """Install a fake agent behind the ``get_agent`` dependency, then clean up."""
    from app.agent.router import get_agent
    from app.main import app

    def _install(agent: PawPilotAgent) -> None:
        app.dependency_overrides[get_agent] = lambda: agent

    try:
        yield _install
    finally:
        app.dependency_overrides.pop(get_agent, None)

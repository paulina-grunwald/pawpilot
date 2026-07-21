"""`run_agent` / `arun_agent` — the typed entrypoints to the Ask PawPilot agent.

A run is: a deterministic red-flag pre-check, the ReAct tool-calling loop over the
vet corpus and web search, then citation resolution over the ids the model cited.
Every run is traced to LangSmith when tracing is enabled.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.store.memory import InMemoryStore
from langsmith import traceable

from app.agent.citations import CitationRegistry, extract_referenced_ids
from app.agent.config import AgentSettings, get_agent_settings
from app.agent.data_tools import SleepDataReader, build_pet_data_tools
from app.agent.datetime_tools import build_datetime_tools
from app.agent.graph import (
    build_agent_graph,
    build_chat_model,
    tool_call_budget_to_recursion_limit,
)
from app.agent.memory import DogMemoryStore
from app.agent.memory_tools import build_memory_tools
from app.agent.pet_food import OpenPetFoodFactsClient, PetFoodLookup
from app.agent.prompt import PROMPT_VERSION, compose_system_prompt
from app.agent.red_flags import EMERGENCY_BANNER, has_red_flag
from app.agent.schemas import AgentAnswer, AgentStreamChunk, AgentStreamFinal
from app.agent.tools import build_agent_tools
from app.agent.verifier import verify_answer
from app.agent.web_search import TavilyWebSearch, WebSearch
from app.rag.observability import configure_langsmith
from app.rag.retriever import VetCorpusRetriever, build_retriever

logger = logging.getLogger(__name__)

_DEFAULT_TOP_K = 6
_MAX_QUERY_LENGTH = 2000
_BUDGET_EXHAUSTED_MESSAGE = (
    "I couldn't finish researching this within my tool-call budget. Please try "
    "rephrasing your question, and contact your veterinarian if this is urgent."
)


def validate_query(query: str) -> None:
    """Reject empty or oversized questions before they reach the model."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if len(query) > _MAX_QUERY_LENGTH:
        raise ValueError(f"query must be at most {_MAX_QUERY_LENGTH} characters")


def _message_text(message: BaseMessage) -> str:
    """Flatten a message's content (string or content blocks) to plain text."""
    content = message.content
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "".join(parts)


class _PreparedRun:
    """Live handles for one run, shared by the sync and async paths.

    A plain class rather than a `BaseModel`: it carries a compiled graph and the
    ``invoked_tools`` accumulator that the tool closures append to by reference —
    Pydantic would copy that list on validation and the appends would be lost.
    """

    def __init__(
        self,
        *,
        graph: Any,
        registry: CitationRegistry,
        invoked_tools: list[str],
        emergency: bool,
        messages: list[BaseMessage],
        config: dict[str, Any],
        system_prompt: str,
    ) -> None:
        self.graph = graph
        self.registry = registry
        self.invoked_tools = invoked_tools
        self.emergency = emergency
        self.messages = messages
        self.config = config
        self.system_prompt = system_prompt


class PawPilotAgent:
    """The agent brain: a chat model plus the corpus and web-search tools.

    Constructed with explicit collaborators so tests can inject a scripted model,
    an in-memory retriever, and a fake web search with no keys or network.
    """

    def __init__(
        self,
        *,
        model: BaseChatModel,
        retriever: VetCorpusRetriever,
        web_search: WebSearch,
        pet_food: PetFoodLookup,
        settings: AgentSettings,
        checkpointer: BaseCheckpointSaver[Any] | None = None,
        memory_store: DogMemoryStore | None = None,
    ) -> None:
        self._model = model
        self._retriever = retriever
        self._web_search = web_search
        self._pet_food = pet_food
        self._settings = settings
        self._checkpointer = checkpointer
        self._memory_store = memory_store

    @property
    def memory_store(self) -> DogMemoryStore | None:
        return self._memory_store

    def _memory_context(self, dog_id: str | None) -> tuple[bool, str]:
        if dog_id is not None and self._memory_store is not None:
            return True, self._memory_store.render_block(dog_id)
        return False, ""

    async def _amemory_context(self, dog_id: str | None) -> tuple[bool, str]:
        if dog_id is not None and self._memory_store is not None:
            return True, await self._memory_store.arender_block(dog_id)
        return False, ""

    def _prepare_run(
        self,
        query: str,
        *,
        top_k: int,
        thread_id: str | None,
        dog_id: str | None,
        memory_active: bool,
        memory_block: str,
        sleep_reader: SleepDataReader | None,
    ) -> _PreparedRun:
        validate_query(query)
        registry = CitationRegistry()
        invoked_tools: list[str] = []
        tools = build_agent_tools(
            self._retriever,
            self._web_search,
            self._pet_food,
            registry,
            invoked_tools,
            top_k=top_k,
        )
        # Always-on: knowing today's date grounds every relative or year-less
        # date the owner names, so the model never has to guess the year.
        tools = tools + build_datetime_tools(invoked_tools)

        if memory_active and self._memory_store is not None and dog_id is not None:
            tools = tools + build_memory_tools(self._memory_store, dog_id, invoked_tools)
        data_active = sleep_reader is not None
        if sleep_reader is not None:
            tools = tools + build_pet_data_tools(sleep_reader, invoked_tools)
        system_prompt = compose_system_prompt(
            memory_block=memory_block,
            include_memory_rule=memory_active,
            include_data_rule=data_active,
        )

        use_thread = thread_id is not None and self._checkpointer is not None
        checkpointer = self._checkpointer if use_thread else None
        graph = build_agent_graph(
            self._model, tools, system_prompt=system_prompt, checkpointer=checkpointer
        )

        config: dict[str, Any] = {
            "recursion_limit": tool_call_budget_to_recursion_limit(
                self._settings.agent_max_tool_calls
            ),
            "run_name": "ask_pawpilot",
            "tags": ["agent", "010c"],
            "metadata": {
                "prompt_version": PROMPT_VERSION,
                "thread_id": thread_id,
                "dog_id": dog_id,
            },
        }
        if use_thread:
            config["configurable"] = {"thread_id": thread_id}

        return _PreparedRun(
            graph=graph,
            registry=registry,
            invoked_tools=invoked_tools,
            emergency=has_red_flag(query),
            messages=[HumanMessage(query)],
            config=config,
            system_prompt=system_prompt,
        )

    def _assemble_answer(self, final_text: str, prepared: _PreparedRun) -> AgentAnswer:
        referenced_ids = extract_referenced_ids(final_text)
        citations = prepared.registry.resolve(referenced_ids)
        verification = verify_answer(
            answer_text=final_text,
            tool_calls=prepared.invoked_tools,
            has_citations=bool(citations),
            system_prompt=prepared.system_prompt,
        )
        if not verification.ok:
            logger.warning("answer verification flags: %s", ", ".join(verification.flags))
        text = EMERGENCY_BANNER + final_text if prepared.emergency else final_text
        return AgentAnswer(
            text=text,
            citations=citations,
            emergency=prepared.emergency,
            tool_calls=list(prepared.invoked_tools),
            contexts=prepared.registry.retrieved_contexts,
        )

    @traceable(run_type="chain", name="ask_pawpilot")
    def run(
        self,
        query: str,
        *,
        thread_id: str | None = None,
        dog_id: str | None = None,
        top_k: int = _DEFAULT_TOP_K,
    ) -> AgentAnswer:
        memory_active, memory_block = self._memory_context(dog_id)
        # The sync path stays corpus/web/memory only: the sleep tool is async-only
        # because it reads the database, and the DB-backed run always uses `arun`.
        prepared = self._prepare_run(
            query,
            top_k=top_k,
            thread_id=thread_id,
            dog_id=dog_id,
            memory_active=memory_active,
            memory_block=memory_block,
            sleep_reader=None,
        )
        try:
            result = prepared.graph.invoke({"messages": prepared.messages}, config=prepared.config)
        except GraphRecursionError:
            return self._assemble_answer(_BUDGET_EXHAUSTED_MESSAGE, prepared)
        return self._assemble_answer(_message_text(result["messages"][-1]), prepared)

    @traceable(run_type="chain", name="ask_pawpilot")
    async def arun(
        self,
        query: str,
        *,
        thread_id: str | None = None,
        dog_id: str | None = None,
        top_k: int = _DEFAULT_TOP_K,
        sleep_reader: SleepDataReader | None = None,
    ) -> AgentAnswer:
        memory_active, memory_block = await self._amemory_context(dog_id)
        prepared = self._prepare_run(
            query,
            top_k=top_k,
            thread_id=thread_id,
            dog_id=dog_id,
            memory_active=memory_active,
            memory_block=memory_block,
            sleep_reader=sleep_reader,
        )
        try:
            result = await prepared.graph.ainvoke(
                {"messages": prepared.messages}, config=prepared.config
            )
        except GraphRecursionError:
            return self._assemble_answer(_BUDGET_EXHAUSTED_MESSAGE, prepared)
        return self._assemble_answer(_message_text(result["messages"][-1]), prepared)

    @traceable(run_type="chain", name="ask_pawpilot")
    async def astream_run(
        self,
        query: str,
        *,
        thread_id: str | None = None,
        dog_id: str | None = None,
        top_k: int = _DEFAULT_TOP_K,
        sleep_reader: SleepDataReader | None = None,
    ) -> AsyncIterator[AgentStreamChunk | AgentStreamFinal]:
        memory_active, memory_block = await self._amemory_context(dog_id)
        prepared = self._prepare_run(
            query,
            top_k=top_k,
            thread_id=thread_id,
            dog_id=dog_id,
            memory_active=memory_active,
            memory_block=memory_block,
            sleep_reader=sleep_reader,
        )
        if prepared.emergency:
            yield AgentStreamChunk(text=EMERGENCY_BANNER)
        answer_parts: list[str] = []
        try:
            async for message_chunk, _metadata in prepared.graph.astream(
                {"messages": prepared.messages},
                config=prepared.config,
                stream_mode="messages",
            ):
                if isinstance(message_chunk, AIMessage):
                    text = _message_text(message_chunk)
                    if text:
                        answer_parts.append(text)
                        yield AgentStreamChunk(text=text)
        except GraphRecursionError:
            yield AgentStreamChunk(text=_BUDGET_EXHAUSTED_MESSAGE)
            yield self._final_event("", prepared)
            return
        yield self._final_event("".join(answer_parts), prepared)

    def _final_event(self, answer_text: str, prepared: _PreparedRun) -> AgentStreamFinal:
        citations = prepared.registry.resolve(extract_referenced_ids(answer_text))
        verification = verify_answer(
            answer_text=answer_text,
            tool_calls=prepared.invoked_tools,
            has_citations=bool(citations),
            system_prompt=prepared.system_prompt,
        )
        if not verification.ok:
            logger.warning("answer verification flags (stream): %s", ", ".join(verification.flags))
        return AgentStreamFinal(
            citations=citations,
            emergency=prepared.emergency,
            tool_calls=list(prepared.invoked_tools),
        )


_default_agent: PawPilotAgent | None = None


def build_agent(
    *,
    checkpointer: BaseCheckpointSaver[Any] | None,
    memory_store: DogMemoryStore | None,
) -> PawPilotAgent:
    """Build an agent from live settings and services with the given memory."""
    configure_langsmith()
    settings = get_agent_settings()
    return PawPilotAgent(
        model=build_chat_model(settings),
        retriever=build_retriever(),
        web_search=TavilyWebSearch(settings),
        pet_food=OpenPetFoodFactsClient(settings),
        settings=settings,
        checkpointer=checkpointer,
        memory_store=memory_store,
    )


def _build_in_memory_agent() -> PawPilotAgent:
    settings = get_agent_settings()
    return build_agent(
        checkpointer=InMemorySaver(),
        memory_store=DogMemoryStore(InMemoryStore(), max_memories=settings.max_dog_memories),
    )


def get_default_agent() -> PawPilotAgent:
    global _default_agent
    if _default_agent is None:
        _default_agent = _build_in_memory_agent()
    return _default_agent


def set_default_agent(agent: PawPilotAgent) -> None:
    global _default_agent
    _default_agent = agent


def clear_default_agent() -> None:
    global _default_agent
    _default_agent = None


def active_memory_store() -> DogMemoryStore | None:
    return _default_agent.memory_store if _default_agent is not None else None


def run_agent(
    query: str,
    *,
    thread_id: str | None = None,
    dog_id: str | None = None,
    top_k: int = _DEFAULT_TOP_K,
) -> AgentAnswer:
    """Answer a dog-health question with a grounded, cited `AgentAnswer`.

    ``thread_id`` continues a conversation (short-term memory); ``dog_id`` recalls
    and updates durable facts about that dog (long-term memory).
    """
    return get_default_agent().run(query, thread_id=thread_id, dog_id=dog_id, top_k=top_k)


async def arun_agent(
    query: str,
    *,
    thread_id: str | None = None,
    dog_id: str | None = None,
    top_k: int = _DEFAULT_TOP_K,
) -> AgentAnswer:
    """Async counterpart to `run_agent` (wrapped by the 010c chat endpoint)."""
    return await get_default_agent().arun(query, thread_id=thread_id, dog_id=dog_id, top_k=top_k)

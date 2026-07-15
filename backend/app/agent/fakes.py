"""Network-free test doubles for the agent: a scripted model and a fake web search.

`ScriptedChatModel` replays a fixed list of assistant turns, choosing the next by
how many assistant messages already exist in the conversation — so a run that
issues a tool call, reads the result, then answers is fully deterministic with no
keys and no network. `FakeWebSearch` returns canned results for the same reason.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable
from pydantic import PrivateAttr

from app.agent.pet_food import PetFoodProduct
from app.agent.web_search import WebSearchResult
from app.integrations.tractive.read_service import SleepSummary


class ScriptedChatModel(BaseChatModel):
    """Replays a scripted list of `AIMessage` turns, one per assistant step.

    Records the messages it receives on each call so tests can assert what reached
    the model — injected long-term memory, or history restored by a checkpointer.
    """

    responses: list[AIMessage]

    _received_batches: list[list[BaseMessage]] = PrivateAttr(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    @property
    def received_batches(self) -> list[list[BaseMessage]]:
        return self._received_batches

    def _next_response(self, messages: list[BaseMessage]) -> AIMessage:
        assistant_turns = sum(1 for message in messages if isinstance(message, AIMessage))
        index = min(assistant_turns, len(self.responses) - 1)
        # Return a fresh copy each time: reusing one object reuses its message id,
        # which the `add_messages` reducer would dedupe, so a looping script would
        # silently terminate instead of running to the tool-call budget.
        return self.responses[index].model_copy(update={"id": None}, deep=True)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self._received_batches.append(list(messages))
        response = self._next_response(messages)
        return ChatResult(generations=[ChatGeneration(message=response)])

    def bind_tools(  # type: ignore[override]  # test double: binding is a no-op
        self, tools: Sequence[Any], **kwargs: Any
    ) -> Runnable[Any, BaseMessage]:
        # The scripted turns already encode which tools to call, so binding is a
        # no-op; return self so `create_agent` can drive this model.
        return self


class FakeWebSearch:
    """Returns a fixed list of web results, ignoring the query."""

    def __init__(self, results: list[WebSearchResult] | None = None) -> None:
        self._results = results if results is not None else []

    def search(self, query: str) -> list[WebSearchResult]:
        return list(self._results)


class FakeSleepReader:
    """Returns a preset `SleepSummary`, recording the day windows it was asked for.

    A network-free stand-in for `TractiveSleepReader` so the sleep tool can be
    exercised without a database.
    """

    def __init__(self, summary: SleepSummary) -> None:
        self._summary = summary
        self.requested_days: list[int] = []

    async def summarize_sleep(self, days: int) -> SleepSummary:
        self.requested_days.append(days)
        return self._summary


class FakePetFood:
    """Returns a fixed list of pet-food products, ignoring the query."""

    def __init__(self, products: list[PetFoodProduct] | None = None) -> None:
        self._products = products if products is not None else []

    def lookup(self, query: str) -> list[PetFoodProduct]:
        return list(self._products)

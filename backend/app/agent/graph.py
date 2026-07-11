"""Build the chat model and compile the prebuilt ReAct agent.

`create_agent` gives the smallest genuinely tool-calling loop; a custom
`StateGraph` arrives in 010b when memory and a verifier node need explicit nodes.
"""

from __future__ import annotations

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agent.config import AgentSettings


def build_chat_model(settings: AgentSettings) -> ChatOpenAI:
    """A low-temperature chat model pointed at the Vercel AI Gateway."""
    return ChatOpenAI(
        base_url=settings.gateway_base_url,
        api_key=settings.gateway_api_key,
        model=settings.agent_model,
        temperature=settings.agent_temperature,
    )


# create_agent's concrete return type is a CompiledStateGraph with four verbose
# generic parameters that shift between LangGraph releases; Any keeps the seam stable.
def build_agent_graph(
    model: BaseChatModel,
    tools: list[BaseTool],
    *,
    system_prompt: str | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Any:
    """Compile the ReAct agent from a chat model, tools, prompt, and memory.

    ``system_prompt`` is applied by the agent on every model call (so it is not
    stored in thread history); ``checkpointer`` gives the run short-term memory
    when invoked with a ``thread_id``.
    """
    return create_agent(model, tools=tools, system_prompt=system_prompt, checkpointer=checkpointer)


def tool_call_budget_to_recursion_limit(max_tool_calls: int) -> int:
    """Translate a tool-call budget into LangGraph's per-run recursion limit.

    Each tool call costs an agent step plus a tool step, and the graph needs a
    final agent step for the answer plus one more to reach the end — so allowing
    ``max_tool_calls`` round trips takes ``2 * max_tool_calls + 2`` graph steps
    (verified against the compiled graph, not just derived).
    """
    return 2 * max_tool_calls + 2

"""Tests for the per-dog memory tools built by `build_memory_tools`.

Each behavior is exercised through BOTH the sync ``.func`` and the async
``.coroutine`` that every `StructuredTool` exposes, so the save/list/delete tools
are verified on whichever path the graph drives them (``invoke`` vs ``ainvoke``).
All of it runs against an `InMemoryStore`, so there is no network or database.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.store.memory import InMemoryStore

from app.agent.memory import DogMemoryStore
from app.agent.memory_tools import build_memory_tools

_DOG_ID = "dog-1"

# --------------------------------------------------------------------------- #
# Local helpers (kept in this file per the "no conftest edits" rule)
# --------------------------------------------------------------------------- #


def _make_store(*, max_memories: int = 20) -> DogMemoryStore:
    """A fresh, empty `DogMemoryStore` over an in-memory backing store."""
    return DogMemoryStore(InMemoryStore(), max_memories=max_memories)


def _build_tools(store: DogMemoryStore) -> tuple[list[BaseTool], list[str]]:
    """Build the three memory tools plus the shared invocation log they append to."""
    invoked_tools: list[str] = []
    tools = build_memory_tools(store, _DOG_ID, invoked_tools)
    return tools, invoked_tools


def _tool_named(tools: list[BaseTool], name: str) -> StructuredTool:
    """Return the single `StructuredTool` with ``name`` from ``tools``."""
    for tool in tools:
        if tool.name == name:
            assert isinstance(tool, StructuredTool)
            return tool
    raise AssertionError(f"no tool named {name!r} in {[tool.name for tool in tools]}")


def _invoke_sync(tool: StructuredTool, **arguments: str) -> str:
    """Drive a tool through its synchronous ``.func`` and return the string result."""
    function = tool.func
    assert function is not None
    result = function(**arguments)
    assert isinstance(result, str)
    return result


async def _invoke_async(tool: StructuredTool, **arguments: str) -> str:
    """Drive a tool through its asynchronous ``.coroutine`` and return the result."""
    coroutine = tool.coroutine
    assert coroutine is not None
    result = await coroutine(**arguments)
    assert isinstance(result, str)
    return result


# --------------------------------------------------------------------------- #
# Tool metadata / shape
# --------------------------------------------------------------------------- #


def test_build_memory_tools_returns_three_named_tools() -> None:
    tools, _invoked = _build_tools(_make_store())
    assert [tool.name for tool in tools] == [
        "save_dog_memory",
        "list_dog_memories",
        "delete_dog_memory",
    ]


def test_every_tool_has_a_non_empty_description() -> None:
    tools, _invoked = _build_tools(_make_store())
    for tool in tools:
        assert tool.description.strip()


def test_every_tool_exposes_both_sync_func_and_async_coroutine() -> None:
    tools, _invoked = _build_tools(_make_store())
    for tool in tools:
        assert isinstance(tool, StructuredTool)
        assert tool.func is not None
        assert tool.coroutine is not None


# --------------------------------------------------------------------------- #
# save_dog_memory
# --------------------------------------------------------------------------- #


def test_save_sync_confirms_and_persists_and_logs_invocation() -> None:
    store = _make_store()
    tools, invoked_tools = _build_tools(store)
    save_tool = _tool_named(tools, "save_dog_memory")

    result = _invoke_sync(save_tool, key="breed", value="Australian Shepherd")

    assert result == "Remembered breed: Australian Shepherd."
    assert invoked_tools == ["save_dog_memory"]
    assert [(memory.key, memory.value) for memory in store.list(_DOG_ID)] == [
        ("breed", "Australian Shepherd")
    ]


async def test_save_async_confirms_and_persists_and_logs_invocation() -> None:
    store = _make_store()
    tools, invoked_tools = _build_tools(store)
    save_tool = _tool_named(tools, "save_dog_memory")

    result = await _invoke_async(save_tool, key="weight", value="22 kg")

    assert result == "Remembered weight: 22 kg."
    assert invoked_tools == ["save_dog_memory"]
    assert [(memory.key, memory.value) for memory in await store.alist(_DOG_ID)] == [
        ("weight", "22 kg")
    ]


def test_save_sync_returns_error_message_when_store_full_without_raising() -> None:
    store = _make_store(max_memories=1)
    store.save(_DOG_ID, "breed", "Australian Shepherd")
    tools, invoked_tools = _build_tools(store)
    save_tool = _tool_named(tools, "save_dog_memory")

    result = _invoke_sync(save_tool, key="allergy:chicken", value="itchy paws")

    assert result == "memory is full (max 1 facts per dog)"
    assert invoked_tools == ["save_dog_memory"]
    # The rejected new key must not have been written.
    assert [memory.key for memory in store.list(_DOG_ID)] == ["breed"]


async def test_save_async_returns_error_message_when_store_full_without_raising() -> None:
    store = _make_store(max_memories=1)
    await store.asave(_DOG_ID, "breed", "Australian Shepherd")
    tools, invoked_tools = _build_tools(store)
    save_tool = _tool_named(tools, "save_dog_memory")

    result = await _invoke_async(save_tool, key="allergy:chicken", value="itchy paws")

    assert result == "memory is full (max 1 facts per dog)"
    assert invoked_tools == ["save_dog_memory"]
    assert [memory.key for memory in await store.alist(_DOG_ID)] == ["breed"]


def test_save_sync_overwrites_existing_key_even_when_store_full() -> None:
    store = _make_store(max_memories=1)
    store.save(_DOG_ID, "breed", "Australian Shepherd")
    tools, _invoked = _build_tools(store)
    save_tool = _tool_named(tools, "save_dog_memory")

    result = _invoke_sync(save_tool, key="breed", value="Border Collie")

    assert result == "Remembered breed: Border Collie."
    assert [(memory.key, memory.value) for memory in store.list(_DOG_ID)] == [
        ("breed", "Border Collie")
    ]


# --------------------------------------------------------------------------- #
# list_dog_memories
# --------------------------------------------------------------------------- #


def test_list_sync_returns_placeholder_when_empty() -> None:
    tools, invoked_tools = _build_tools(_make_store())
    list_tool = _tool_named(tools, "list_dog_memories")

    result = _invoke_sync(list_tool)

    assert result == "Nothing is remembered about this dog yet."
    assert invoked_tools == ["list_dog_memories"]


async def test_list_async_returns_placeholder_when_empty() -> None:
    tools, invoked_tools = _build_tools(_make_store())
    list_tool = _tool_named(tools, "list_dog_memories")

    result = await _invoke_async(list_tool)

    assert result == "Nothing is remembered about this dog yet."
    assert invoked_tools == ["list_dog_memories"]


def test_list_sync_returns_newline_joined_key_value_pairs() -> None:
    store = _make_store()
    store.save(_DOG_ID, "breed", "Australian Shepherd")
    store.save(_DOG_ID, "weight", "22 kg")
    tools, invoked_tools = _build_tools(store)
    list_tool = _tool_named(tools, "list_dog_memories")

    result = _invoke_sync(list_tool)

    assert invoked_tools == ["list_dog_memories"]
    lines = result.split("\n")
    assert set(lines) == {"breed: Australian Shepherd", "weight: 22 kg"}


async def test_list_async_returns_newline_joined_key_value_pairs() -> None:
    store = _make_store()
    await store.asave(_DOG_ID, "breed", "Australian Shepherd")
    await store.asave(_DOG_ID, "weight", "22 kg")
    tools, invoked_tools = _build_tools(store)
    list_tool = _tool_named(tools, "list_dog_memories")

    result = await _invoke_async(list_tool)

    assert invoked_tools == ["list_dog_memories"]
    lines = result.split("\n")
    assert set(lines) == {"breed: Australian Shepherd", "weight: 22 kg"}


def test_list_sync_reflects_a_save_made_through_the_save_tool() -> None:
    store = _make_store()
    tools, _invoked = _build_tools(store)
    save_tool = _tool_named(tools, "save_dog_memory")
    list_tool = _tool_named(tools, "list_dog_memories")

    _invoke_sync(save_tool, key="condition", value="hip dysplasia")

    assert _invoke_sync(list_tool) == "condition: hip dysplasia"


# --------------------------------------------------------------------------- #
# delete_dog_memory
# --------------------------------------------------------------------------- #


def test_delete_sync_returns_forgot_when_key_present() -> None:
    store = _make_store()
    store.save(_DOG_ID, "breed", "Australian Shepherd")
    tools, invoked_tools = _build_tools(store)
    delete_tool = _tool_named(tools, "delete_dog_memory")

    result = _invoke_sync(delete_tool, key="breed")

    assert result == "Forgot breed."
    assert invoked_tools == ["delete_dog_memory"]
    assert store.list(_DOG_ID) == []


async def test_delete_async_returns_forgot_when_key_present() -> None:
    store = _make_store()
    await store.asave(_DOG_ID, "breed", "Australian Shepherd")
    tools, invoked_tools = _build_tools(store)
    delete_tool = _tool_named(tools, "delete_dog_memory")

    result = await _invoke_async(delete_tool, key="breed")

    assert result == "Forgot breed."
    assert invoked_tools == ["delete_dog_memory"]
    assert await store.alist(_DOG_ID) == []


def test_delete_sync_reports_missing_key_when_absent() -> None:
    tools, invoked_tools = _build_tools(_make_store())
    delete_tool = _tool_named(tools, "delete_dog_memory")

    result = _invoke_sync(delete_tool, key="ghost")

    assert result == "No remembered fact named ghost."
    assert invoked_tools == ["delete_dog_memory"]


async def test_delete_async_reports_missing_key_when_absent() -> None:
    tools, invoked_tools = _build_tools(_make_store())
    delete_tool = _tool_named(tools, "delete_dog_memory")

    result = await _invoke_async(delete_tool, key="ghost")

    assert result == "No remembered fact named ghost."
    assert invoked_tools == ["delete_dog_memory"]


# --------------------------------------------------------------------------- #
# Shared invocation log across tools
# --------------------------------------------------------------------------- #


def test_invoked_tools_accumulates_in_call_order_across_tools() -> None:
    store = _make_store()
    tools, invoked_tools = _build_tools(store)
    save_tool = _tool_named(tools, "save_dog_memory")
    list_tool = _tool_named(tools, "list_dog_memories")
    delete_tool = _tool_named(tools, "delete_dog_memory")

    _invoke_sync(save_tool, key="breed", value="Australian Shepherd")
    _invoke_sync(list_tool)
    _invoke_sync(delete_tool, key="breed")

    assert invoked_tools == [
        "save_dog_memory",
        "list_dog_memories",
        "delete_dog_memory",
    ]


async def test_invoked_tools_records_async_paths_too() -> None:
    store = _make_store()
    tools, invoked_tools = _build_tools(store)
    save_tool = _tool_named(tools, "save_dog_memory")
    delete_tool = _tool_named(tools, "delete_dog_memory")

    await _invoke_async(save_tool, key="breed", value="Australian Shepherd")
    await _invoke_async(delete_tool, key="breed")

    assert invoked_tools == ["save_dog_memory", "delete_dog_memory"]

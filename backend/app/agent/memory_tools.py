"""Per-dog memory tools, bound to one run's dog and store.

Each tool carries both a sync and an async implementation so the same tool works
whether the graph is driven by ``invoke`` (in-memory) or ``ainvoke`` (Postgres).
Every tool records its name in ``invoked_tools`` so a run reports what executed.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, StructuredTool

from app.agent.memory import DogMemory, DogMemoryStore

_SAVE_DESCRIPTION = (
    "Remember a durable, owner-confirmed fact about this dog, such as its breed, "
    "age, weight, a diagnosed condition, a known allergy, or a current medication. "
    'Use a short stable key (e.g. "breed", "allergy:chicken"). Only save facts the '
    "owner has explicitly stated about their own dog."
)
_LIST_DESCRIPTION = "List everything currently remembered about this dog."
_DELETE_DESCRIPTION = "Forget one remembered fact about this dog by its key."


def build_memory_tools(
    store: DogMemoryStore, dog_id: str, invoked_tools: list[str]
) -> list[BaseTool]:
    """Build the save/list/delete memory tools scoped to ``dog_id``."""

    def save_dog_memory(key: str, value: str) -> str:
        invoked_tools.append("save_dog_memory")
        try:
            store.save(dog_id, key, value)
        except ValueError as error:
            return str(error)
        return f"Remembered {key}: {value}."

    async def asave_dog_memory(key: str, value: str) -> str:
        invoked_tools.append("save_dog_memory")
        try:
            await store.asave(dog_id, key, value)
        except ValueError as error:
            return str(error)
        return f"Remembered {key}: {value}."

    def list_dog_memories() -> str:
        invoked_tools.append("list_dog_memories")
        return _render_list(store.list(dog_id))

    async def alist_dog_memories() -> str:
        invoked_tools.append("list_dog_memories")
        return _render_list(await store.alist(dog_id))

    def delete_dog_memory(key: str) -> str:
        invoked_tools.append("delete_dog_memory")
        return _render_delete(key, store.delete(dog_id, key))

    async def adelete_dog_memory(key: str) -> str:
        invoked_tools.append("delete_dog_memory")
        return _render_delete(key, await store.adelete(dog_id, key))

    return [
        StructuredTool.from_function(
            func=save_dog_memory,
            coroutine=asave_dog_memory,
            name="save_dog_memory",
            description=_SAVE_DESCRIPTION,
        ),
        StructuredTool.from_function(
            func=list_dog_memories,
            coroutine=alist_dog_memories,
            name="list_dog_memories",
            description=_LIST_DESCRIPTION,
        ),
        StructuredTool.from_function(
            func=delete_dog_memory,
            coroutine=adelete_dog_memory,
            name="delete_dog_memory",
            description=_DELETE_DESCRIPTION,
        ),
    ]


def _render_list(memories: list[DogMemory]) -> str:
    if not memories:
        return "Nothing is remembered about this dog yet."
    return "\n".join(f"{memory.key}: {memory.value}" for memory in memories)


def _render_delete(key: str, deleted: bool) -> str:
    return f"Forgot {key}." if deleted else f"No remembered fact named {key}."

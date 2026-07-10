"""Per-dog memory tools, bound to one run's dog and store.

Mirrors the course's save/list/delete memory-tool pattern. The tools are only
attached when a run has a ``dog_id``; each records its name in ``invoked_tools``
(like the retrieval tools) so the run reports what actually executed.
"""

from __future__ import annotations

from langchain_core.tools import BaseTool, tool

from app.agent.memory import DogMemoryStore


def build_memory_tools(
    store: DogMemoryStore, dog_id: str, invoked_tools: list[str]
) -> list[BaseTool]:
    """Build the save/list/delete memory tools scoped to ``dog_id``."""

    @tool
    def save_dog_memory(key: str, value: str) -> str:
        """Remember a durable, owner-confirmed fact about this dog, such as its
        breed, age, weight, a diagnosed condition, a known allergy, or a current
        medication. Use a short stable key (e.g. "breed", "allergy:chicken").
        Only save facts the owner has explicitly stated about their own dog."""
        invoked_tools.append("save_dog_memory")
        try:
            store.save(dog_id, key, value)
        except ValueError as error:
            return str(error)
        return f"Remembered {key}: {value}."

    @tool
    def list_dog_memories() -> str:
        """List everything currently remembered about this dog."""
        invoked_tools.append("list_dog_memories")
        memories = store.list(dog_id)
        if not memories:
            return "Nothing is remembered about this dog yet."
        return "\n".join(f"{memory.key}: {memory.value}" for memory in memories)

    @tool
    def delete_dog_memory(key: str) -> str:
        """Forget one remembered fact about this dog by its key."""
        invoked_tools.append("delete_dog_memory")
        deleted = store.delete(dog_id, key)
        return f"Forgot {key}." if deleted else f"No remembered fact named {key}."

    return [save_dog_memory, list_dog_memories, delete_dog_memory]

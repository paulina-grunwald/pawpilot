"""Long-term, per-dog memory over a LangGraph store.

`DogMemoryStore` wraps a `BaseStore` with a fixed ``("dog", dog_id)`` namespace so
durable facts about one dog (breed, age, weight, conditions, allergies) survive
across conversation threads and sessions. At the start of a run the runner renders
these facts into a system-prompt block; the agent writes them via the memory tools.
"""

from __future__ import annotations

from langgraph.store.base import BaseStore
from pydantic import BaseModel

_VALUE_FIELD = "value"


class DogMemory(BaseModel):
    """A single durable fact about a dog, keyed by a stable slug."""

    key: str
    value: str


DogMemories = list[DogMemory]


class DogMemoryStore:
    """Per-dog durable memory backed by a LangGraph ``BaseStore``."""

    def __init__(self, store: BaseStore, *, max_memories: int = 20) -> None:
        self._store = store
        self._max_memories = max_memories

    def _namespace(self, dog_id: str) -> tuple[str, str]:
        return ("dog", dog_id)

    def save(self, dog_id: str, key: str, value: str) -> DogMemory:
        namespace = self._namespace(dog_id)
        is_new_key = self._store.get(namespace, key) is None
        if is_new_key and len(self.list(dog_id)) >= self._max_memories:
            raise ValueError(f"memory is full (max {self._max_memories} facts per dog)")
        self._store.put(namespace, key, {_VALUE_FIELD: value})
        return DogMemory(key=key, value=value)

    async def asave(self, dog_id: str, key: str, value: str) -> DogMemory:
        namespace = self._namespace(dog_id)
        is_new_key = (await self._store.aget(namespace, key)) is None
        if is_new_key and len(await self.alist(dog_id)) >= self._max_memories:
            raise ValueError(f"memory is full (max {self._max_memories} facts per dog)")
        await self._store.aput(namespace, key, {_VALUE_FIELD: value})
        return DogMemory(key=key, value=value)

    def list(self, dog_id: str) -> DogMemories:
        items = self._store.search(self._namespace(dog_id), limit=self._max_memories)
        return [
            DogMemory(key=item.key, value=str(item.value.get(_VALUE_FIELD, ""))) for item in items
        ]

    async def alist(self, dog_id: str) -> DogMemories:
        items = await self._store.asearch(self._namespace(dog_id), limit=self._max_memories)
        return [
            DogMemory(key=item.key, value=str(item.value.get(_VALUE_FIELD, ""))) for item in items
        ]

    def delete(self, dog_id: str, key: str) -> bool:
        if self._store.get(self._namespace(dog_id), key) is None:
            return False
        self._store.delete(self._namespace(dog_id), key)
        return True

    async def adelete(self, dog_id: str, key: str) -> bool:
        if (await self._store.aget(self._namespace(dog_id), key)) is None:
            return False
        await self._store.adelete(self._namespace(dog_id), key)
        return True

    async def aclear(self, dog_id: str) -> None:
        namespace = self._namespace(dog_id)
        for memory in await self.alist(dog_id):
            await self._store.adelete(namespace, memory.key)

    def render_block(self, dog_id: str) -> str:
        return self._render(self.list(dog_id))

    async def arender_block(self, dog_id: str) -> str:
        return self._render(await self.alist(dog_id))

    @staticmethod
    def _render(memories: DogMemories) -> str:
        if not memories:
            return ""
        lines = [f"- {memory.key}: {memory.value}" for memory in memories]
        return "What you already know about this dog:\n" + "\n".join(lines)

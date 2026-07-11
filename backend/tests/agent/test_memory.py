"""Tests for `DogMemoryStore`, the per-dog long-term memory over a LangGraph store.

These drive a real `InMemoryStore` (network-free) through both the sync and async
faces of the wrapper: save/list, the per-dog cap, key updates, deletion, clearing,
namespace isolation, and system-prompt block rendering.
"""

from __future__ import annotations

import pytest
from langgraph.store.memory import InMemoryStore

from app.agent.memory import DogMemory, DogMemoryStore


def make_store(max_memories: int = 20) -> DogMemoryStore:
    """A `DogMemoryStore` over a fresh in-memory LangGraph store."""
    return DogMemoryStore(InMemoryStore(), max_memories=max_memories)


# --------------------------------------------------------------------------- #
# DogMemory model
# --------------------------------------------------------------------------- #


def test_dog_memory_is_a_pydantic_model() -> None:
    memory = DogMemory(key="breed", value="Australian Shepherd")
    assert memory.model_dump() == {"key": "breed", "value": "Australian Shepherd"}


# --------------------------------------------------------------------------- #
# save / asave — happy path
# --------------------------------------------------------------------------- #


def test_save_returns_dog_memory_with_key_and_value() -> None:
    store = make_store()
    saved = store.save("dog-1", "breed", "Australian Shepherd")
    assert saved == DogMemory(key="breed", value="Australian Shepherd")


def test_save_persists_fact_so_list_returns_it() -> None:
    store = make_store()
    store.save("dog-1", "breed", "Australian Shepherd")
    assert store.list("dog-1") == [DogMemory(key="breed", value="Australian Shepherd")]


async def test_asave_returns_dog_memory_with_key_and_value() -> None:
    store = make_store()
    saved = await store.asave("dog-1", "weight", "22kg")
    assert saved == DogMemory(key="weight", value="22kg")


async def test_asave_persists_fact_so_alist_returns_it() -> None:
    store = make_store()
    await store.asave("dog-1", "weight", "22kg")
    assert await store.alist("dog-1") == [DogMemory(key="weight", value="22kg")]


# --------------------------------------------------------------------------- #
# list / alist — multiple facts
# --------------------------------------------------------------------------- #


def test_list_returns_all_stored_facts() -> None:
    store = make_store()
    store.save("dog-1", "breed", "Aussie")
    store.save("dog-1", "age", "4 years")
    listed = {memory.key: memory.value for memory in store.list("dog-1")}
    assert listed == {"breed": "Aussie", "age": "4 years"}


def test_list_is_empty_for_unknown_dog() -> None:
    store = make_store()
    assert store.list("nobody") == []


async def test_alist_returns_all_stored_facts() -> None:
    store = make_store()
    await store.asave("dog-1", "breed", "Aussie")
    await store.asave("dog-1", "allergy", "chicken")
    listed = {memory.key: memory.value for memory in await store.alist("dog-1")}
    assert listed == {"breed": "Aussie", "allergy": "chicken"}


async def test_alist_is_empty_for_unknown_dog() -> None:
    store = make_store()
    assert await store.alist("nobody") == []


# --------------------------------------------------------------------------- #
# Updating an existing key overwrites and does not count against the cap
# --------------------------------------------------------------------------- #


def test_save_overwrites_value_for_existing_key() -> None:
    store = make_store()
    store.save("dog-1", "weight", "20kg")
    updated = store.save("dog-1", "weight", "22kg")
    assert updated == DogMemory(key="weight", value="22kg")
    assert store.list("dog-1") == [DogMemory(key="weight", value="22kg")]


def test_updating_existing_key_does_not_grow_the_count() -> None:
    store = make_store()
    store.save("dog-1", "weight", "20kg")
    store.save("dog-1", "weight", "22kg")
    store.save("dog-1", "weight", "24kg")
    assert len(store.list("dog-1")) == 1


async def test_asave_overwrites_value_for_existing_key() -> None:
    store = make_store()
    await store.asave("dog-1", "weight", "20kg")
    updated = await store.asave("dog-1", "weight", "22kg")
    assert updated == DogMemory(key="weight", value="22kg")
    assert await store.alist("dog-1") == [DogMemory(key="weight", value="22kg")]


# --------------------------------------------------------------------------- #
# Cap: max_memories limits distinct NEW keys
# --------------------------------------------------------------------------- #


def test_save_raises_when_a_new_key_exceeds_the_cap() -> None:
    store = make_store(max_memories=2)
    store.save("dog-1", "breed", "Aussie")
    store.save("dog-1", "age", "4 years")
    with pytest.raises(ValueError, match="memory is full"):
        store.save("dog-1", "weight", "22kg")


def test_cap_error_message_names_the_limit() -> None:
    store = make_store(max_memories=2)
    store.save("dog-1", "breed", "Aussie")
    store.save("dog-1", "age", "4 years")
    with pytest.raises(ValueError, match=r"memory is full \(max 2 facts per dog\)"):
        store.save("dog-1", "weight", "22kg")


def test_resaving_existing_key_is_allowed_when_full() -> None:
    store = make_store(max_memories=2)
    store.save("dog-1", "breed", "Aussie")
    store.save("dog-1", "age", "4 years")
    updated = store.save("dog-1", "age", "5 years")
    assert updated == DogMemory(key="age", value="5 years")
    listed = {memory.key: memory.value for memory in store.list("dog-1")}
    assert listed == {"breed": "Aussie", "age": "5 years"}


async def test_asave_raises_when_a_new_key_exceeds_the_cap() -> None:
    store = make_store(max_memories=2)
    await store.asave("dog-1", "breed", "Aussie")
    await store.asave("dog-1", "age", "4 years")
    with pytest.raises(ValueError, match=r"memory is full \(max 2 facts per dog\)"):
        await store.asave("dog-1", "weight", "22kg")


async def test_aresaving_existing_key_is_allowed_when_full() -> None:
    store = make_store(max_memories=2)
    await store.asave("dog-1", "breed", "Aussie")
    await store.asave("dog-1", "age", "4 years")
    updated = await store.asave("dog-1", "age", "5 years")
    assert updated == DogMemory(key="age", value="5 years")


# --------------------------------------------------------------------------- #
# delete / adelete
# --------------------------------------------------------------------------- #


def test_delete_returns_true_and_removes_the_fact() -> None:
    store = make_store()
    store.save("dog-1", "breed", "Aussie")
    assert store.delete("dog-1", "breed") is True
    assert store.list("dog-1") == []


def test_delete_returns_false_for_missing_key() -> None:
    store = make_store()
    assert store.delete("dog-1", "breed") is False


def test_delete_leaves_other_facts_intact() -> None:
    store = make_store()
    store.save("dog-1", "breed", "Aussie")
    store.save("dog-1", "age", "4 years")
    assert store.delete("dog-1", "breed") is True
    assert store.list("dog-1") == [DogMemory(key="age", value="4 years")]


async def test_adelete_returns_true_and_removes_the_fact() -> None:
    store = make_store()
    await store.asave("dog-1", "breed", "Aussie")
    assert await store.adelete("dog-1", "breed") is True
    assert await store.alist("dog-1") == []


async def test_adelete_returns_false_for_missing_key() -> None:
    store = make_store()
    assert await store.adelete("dog-1", "breed") is False


async def test_adelete_leaves_other_facts_intact() -> None:
    store = make_store()
    await store.asave("dog-1", "breed", "Aussie")
    await store.asave("dog-1", "age", "4 years")
    assert await store.adelete("dog-1", "breed") is True
    assert await store.alist("dog-1") == [DogMemory(key="age", value="4 years")]


async def test_adelete_on_one_dog_does_not_affect_another() -> None:
    store = make_store()
    await store.asave("dog-1", "breed", "Aussie")
    await store.asave("dog-2", "breed", "Corgi")
    assert await store.adelete("dog-1", "breed") is True
    assert await store.alist("dog-1") == []
    assert await store.alist("dog-2") == [DogMemory(key="breed", value="Corgi")]


# --------------------------------------------------------------------------- #
# list / alist — value coercion of malformed stored payloads
# --------------------------------------------------------------------------- #


def test_list_coerces_missing_value_field_to_empty_string() -> None:
    backing_store = InMemoryStore()
    store = DogMemoryStore(backing_store)
    # Write past the public API to a raw payload with no "value" key; mirrors the
    # ("dog", dog_id) namespace DogMemoryStore uses internally.
    backing_store.put(("dog", "dog-1"), "breed", {"unexpected": "shape"})
    assert store.list("dog-1") == [DogMemory(key="breed", value="")]


async def test_alist_coerces_non_string_value_to_string() -> None:
    backing_store = InMemoryStore()
    store = DogMemoryStore(backing_store)
    backing_store.put(("dog", "dog-1"), "age", {"value": 4})
    assert await store.alist("dog-1") == [DogMemory(key="age", value="4")]


# --------------------------------------------------------------------------- #
# aclear
# --------------------------------------------------------------------------- #


async def test_aclear_removes_all_facts_for_a_dog() -> None:
    store = make_store()
    await store.asave("dog-1", "breed", "Aussie")
    await store.asave("dog-1", "age", "4 years")
    await store.aclear("dog-1")
    assert await store.alist("dog-1") == []


async def test_aclear_on_empty_dog_is_a_noop() -> None:
    store = make_store()
    await store.aclear("dog-1")
    assert await store.alist("dog-1") == []


async def test_aclear_leaves_other_dogs_untouched() -> None:
    store = make_store()
    await store.asave("dog-a", "breed", "Aussie")
    await store.asave("dog-b", "breed", "Beagle")
    await store.aclear("dog-a")
    assert await store.alist("dog-a") == []
    assert await store.alist("dog-b") == [DogMemory(key="breed", value="Beagle")]


# --------------------------------------------------------------------------- #
# Namespace isolation between dogs
# --------------------------------------------------------------------------- #


def test_facts_are_isolated_per_dog() -> None:
    store = make_store()
    store.save("dog-a", "breed", "Aussie")
    assert store.list("dog-b") == []
    assert store.list("dog-a") == [DogMemory(key="breed", value="Aussie")]


def test_same_key_holds_independent_values_per_dog() -> None:
    store = make_store()
    store.save("dog-a", "breed", "Aussie")
    store.save("dog-b", "breed", "Beagle")
    assert store.list("dog-a") == [DogMemory(key="breed", value="Aussie")]
    assert store.list("dog-b") == [DogMemory(key="breed", value="Beagle")]


def test_cap_is_tracked_independently_per_dog() -> None:
    store = make_store(max_memories=1)
    store.save("dog-a", "breed", "Aussie")
    # dog-b has its own budget, so this first NEW key must be allowed.
    store.save("dog-b", "breed", "Beagle")
    assert store.list("dog-a") == [DogMemory(key="breed", value="Aussie")]
    assert store.list("dog-b") == [DogMemory(key="breed", value="Beagle")]


def test_delete_on_one_dog_does_not_affect_another() -> None:
    store = make_store()
    store.save("dog-a", "breed", "Aussie")
    store.save("dog-b", "breed", "Beagle")
    assert store.delete("dog-a", "breed") is True
    assert store.list("dog-b") == [DogMemory(key="breed", value="Beagle")]


# --------------------------------------------------------------------------- #
# render_block / arender_block
# --------------------------------------------------------------------------- #


def test_render_block_is_empty_string_when_no_facts() -> None:
    store = make_store()
    assert store.render_block("dog-1") == ""


def test_render_block_has_header_and_one_line_per_fact() -> None:
    store = make_store()
    store.save("dog-1", "breed", "Aussie")
    store.save("dog-1", "age", "4 years")
    block = store.render_block("dog-1")
    assert block.startswith("What you already know about this dog:")
    assert "- breed: Aussie" in block
    assert "- age: 4 years" in block


def test_render_block_renders_a_single_fact_line() -> None:
    store = make_store()
    store.save("dog-1", "breed", "Aussie")
    assert store.render_block("dog-1") == ("What you already know about this dog:\n- breed: Aussie")


async def test_arender_block_is_empty_string_when_no_facts() -> None:
    store = make_store()
    assert await store.arender_block("dog-1") == ""


async def test_arender_block_has_header_and_one_line_per_fact() -> None:
    store = make_store()
    await store.asave("dog-1", "breed", "Aussie")
    await store.asave("dog-1", "allergy", "chicken")
    block = await store.arender_block("dog-1")
    assert block.startswith("What you already know about this dog:")
    assert "- breed: Aussie" in block
    assert "- allergy: chicken" in block

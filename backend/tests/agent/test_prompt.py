"""Tests for the Ask PawPilot system-prompt composition module.

`app.agent.prompt` is pure string assembly, so these tests assert on the real
constants and the exact layout produced by `compose_system_prompt` — no agent,
no network, no DB.
"""

from __future__ import annotations

from app.agent.prompt import (
    MEMORY_WRITE_RULE,
    PROMPT_VERSION,
    REFUSAL_MESSAGE,
    SCOPE_RULE,
    SYSTEM_PROMPT,
    VET_DISCLAIMER,
    compose_system_prompt,
)

# --------------------------------------------------------------------------- #
# Module-level constants
# --------------------------------------------------------------------------- #


def test_prompt_version_is_non_empty_string() -> None:
    assert isinstance(PROMPT_VERSION, str)
    assert PROMPT_VERSION != ""


def test_prompt_version_pins_the_guardrail_revision() -> None:

    assert PROMPT_VERSION == "014-1"

# Scope guardrail constants

def test_refusal_message_is_non_empty_string() -> None:
    assert isinstance(REFUSAL_MESSAGE, str)
    assert REFUSAL_MESSAGE != ""


def test_refusal_message_names_the_dog_domain() -> None:
    assert "dog" in REFUSAL_MESSAGE.lower()


def test_scope_rule_is_non_empty_string() -> None:
    assert isinstance(SCOPE_RULE, str)
    assert SCOPE_RULE != ""


def test_scope_rule_embeds_the_canonical_refusal_message() -> None:

    assert REFUSAL_MESSAGE in SCOPE_RULE


def test_scope_rule_restricts_to_dogs_with_an_off_topic_example() -> None:
    lowered = SCOPE_RULE.lower()
    assert "only help with dogs" in lowered
    assert "weather" in lowered


def test_scope_rule_keeps_euthanasia_boundary_in_scope() -> None:
    # Boundary case #15 ("should I put him down?") is in-domain; the scope rule
    # must not let the model refuse it as off-topic.
    assert "euthanize" in SCOPE_RULE.lower()


def test_system_prompt_contains_scope_rule_and_refusal() -> None:
    assert SCOPE_RULE in SYSTEM_PROMPT
    assert REFUSAL_MESSAGE in SYSTEM_PROMPT


def test_scope_rule_precedes_the_tool_section() -> None:
    assert SYSTEM_PROMPT.index(SCOPE_RULE) < SYSTEM_PROMPT.index("retrieve_vet_corpus")


def test_vet_disclaimer_is_non_empty_string() -> None:
    assert isinstance(VET_DISCLAIMER, str)
    assert VET_DISCLAIMER != ""


def test_memory_write_rule_is_non_empty_string() -> None:
    assert isinstance(MEMORY_WRITE_RULE, str)
    assert MEMORY_WRITE_RULE != ""


def test_memory_write_rule_mentions_save_dog_memory() -> None:
    assert "save_dog_memory" in MEMORY_WRITE_RULE


def test_system_prompt_contains_vet_disclaimer() -> None:
    assert VET_DISCLAIMER in SYSTEM_PROMPT


def test_system_prompt_mentions_both_tools() -> None:
    assert "retrieve_vet_corpus" in SYSTEM_PROMPT
    assert "web_search" in SYSTEM_PROMPT


# --------------------------------------------------------------------------- #
# compose_system_prompt — base only
# --------------------------------------------------------------------------- #


def test_compose_with_no_args_returns_base_prompt_only() -> None:
    assert compose_system_prompt() == SYSTEM_PROMPT


def test_compose_with_no_args_omits_memory_write_rule() -> None:
    assert MEMORY_WRITE_RULE not in compose_system_prompt()


def test_compose_base_contains_disclaimer_and_tool_mentions() -> None:
    prompt = compose_system_prompt()
    assert VET_DISCLAIMER in prompt
    assert "retrieve_vet_corpus" in prompt
    assert "web_search" in prompt


# --------------------------------------------------------------------------- #
# compose_system_prompt — memory rule
# --------------------------------------------------------------------------- #


def test_compose_appends_memory_write_rule_when_requested() -> None:
    prompt = compose_system_prompt(include_memory_rule=True)
    assert prompt == f"{SYSTEM_PROMPT}\n\n{MEMORY_WRITE_RULE}"


def test_compose_memory_rule_starts_with_base_prompt() -> None:
    prompt = compose_system_prompt(include_memory_rule=True)
    assert prompt.startswith(SYSTEM_PROMPT)
    assert MEMORY_WRITE_RULE in prompt


def test_compose_memory_rule_mentions_save_dog_memory() -> None:
    assert "save_dog_memory" in compose_system_prompt(include_memory_rule=True)


def test_compose_include_memory_rule_false_is_base_only() -> None:
    assert compose_system_prompt(include_memory_rule=False) == SYSTEM_PROMPT


# --------------------------------------------------------------------------- #
# compose_system_prompt — memory block
# --------------------------------------------------------------------------- #


def test_compose_appends_memory_block_verbatim() -> None:
    memory_block = "Known facts about Rex:\n- breed: Australian Shepherd"
    prompt = compose_system_prompt(memory_block=memory_block)
    assert prompt == f"{SYSTEM_PROMPT}\n\n{memory_block}"


def test_compose_memory_block_content_appears_verbatim() -> None:
    memory_block = "Known facts about Rex:\n- breed: Australian Shepherd"
    assert memory_block in compose_system_prompt(memory_block=memory_block)


def test_compose_empty_memory_block_is_not_appended() -> None:
    assert compose_system_prompt(memory_block="") == SYSTEM_PROMPT


def test_compose_default_memory_block_is_base_only() -> None:
    assert compose_system_prompt() == SYSTEM_PROMPT


# --------------------------------------------------------------------------- #
# compose_system_prompt — rule and block together
# --------------------------------------------------------------------------- #


def test_compose_includes_rule_and_block_in_order() -> None:
    memory_block = "Known facts about Rex:\n- age: 4 years"
    prompt = compose_system_prompt(memory_block=memory_block, include_memory_rule=True)
    assert prompt == f"{SYSTEM_PROMPT}\n\n{MEMORY_WRITE_RULE}\n\n{memory_block}"


def test_compose_rule_precedes_block() -> None:
    memory_block = "Known facts about Rex:\n- age: 4 years"
    prompt = compose_system_prompt(memory_block=memory_block, include_memory_rule=True)
    base_position = prompt.index(SYSTEM_PROMPT)
    rule_position = prompt.index(MEMORY_WRITE_RULE)
    block_position = prompt.index(memory_block)
    assert base_position < rule_position < block_position


def test_compose_sections_separated_by_blank_lines() -> None:
    memory_block = "Known facts about Rex:\n- age: 4 years"
    prompt = compose_system_prompt(memory_block=memory_block, include_memory_rule=True)
    assert f"\n\n{MEMORY_WRITE_RULE}\n\n{memory_block}" in prompt


def test_compose_rule_true_empty_block_appends_only_rule() -> None:
    prompt = compose_system_prompt(memory_block="", include_memory_rule=True)
    assert prompt == f"{SYSTEM_PROMPT}\n\n{MEMORY_WRITE_RULE}"

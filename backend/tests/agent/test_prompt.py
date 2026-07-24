"""Tests for the Ask PawPilot system-prompt composition module.

`app.agent.prompt` is pure string assembly, so these tests assert on the real
constants and the exact layout produced by `compose_system_prompt` — no agent,
no network, no DB.
"""

from __future__ import annotations

from app.agent.prompt import (
    DATA_TOOL_RULE,
    MEMORY_WRITE_RULE,
    OFF_TOPIC_MESSAGE,
    PROMPT_VERSION,
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


def test_vet_disclaimer_is_non_empty_string() -> None:
    assert isinstance(VET_DISCLAIMER, str)
    assert VET_DISCLAIMER != ""


def test_memory_write_rule_is_non_empty_string() -> None:
    assert isinstance(MEMORY_WRITE_RULE, str)
    assert MEMORY_WRITE_RULE != ""


def test_memory_write_rule_mentions_save_dog_memory() -> None:
    assert "save_dog_memory" in MEMORY_WRITE_RULE


def test_data_tool_rule_is_non_empty_string() -> None:
    assert isinstance(DATA_TOOL_RULE, str)
    assert DATA_TOOL_RULE != ""


def test_data_tool_rule_mentions_get_dog_metric() -> None:
    assert "get_dog_metric" in DATA_TOOL_RULE


def test_data_tool_rule_mentions_get_dog_health_snapshot() -> None:
    assert "get_dog_health_snapshot" in DATA_TOOL_RULE


def test_data_tool_rule_carries_the_tracker_caveats() -> None:
    """The caveats are the difference between a figure and an overclaim."""
    assert "floor" in DATA_TOOL_RULE
    assert "never clinical" in DATA_TOOL_RULE


def test_data_tool_rule_tells_the_model_to_abstain_on_unmeasured_things() -> None:
    assert "does not record it" in DATA_TOOL_RULE


def test_data_tool_rule_mentions_get_current_date_for_resolution() -> None:
    assert "get_current_date" in DATA_TOOL_RULE


def test_system_prompt_contains_vet_disclaimer() -> None:
    assert VET_DISCLAIMER in SYSTEM_PROMPT


def test_system_prompt_mentions_both_tools() -> None:
    assert "retrieve_vet_corpus" in SYSTEM_PROMPT
    assert "web_search" in SYSTEM_PROMPT


def test_system_prompt_mentions_the_always_on_clock_tool() -> None:
    assert "get_current_date" in SYSTEM_PROMPT


def test_off_topic_message_is_non_empty_string() -> None:
    assert isinstance(OFF_TOPIC_MESSAGE, str)
    assert OFF_TOPIC_MESSAGE != ""


def test_off_topic_message_redirects_to_dog_topics() -> None:
    assert "dog" in OFF_TOPIC_MESSAGE


def test_system_prompt_contains_off_topic_message() -> None:
    assert OFF_TOPIC_MESSAGE in SYSTEM_PROMPT


def test_system_prompt_declares_dog_only_scope() -> None:
    assert "Scope: you answer only dog-related questions." in SYSTEM_PROMPT


def test_system_prompt_marks_non_dog_questions_out_of_scope() -> None:
    assert "out of scope" in SYSTEM_PROMPT


def test_system_prompt_forbids_tool_calls_for_off_topic_questions() -> None:
    assert "do not call any tool" in SYSTEM_PROMPT


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
# compose_system_prompt — data-tool rule
# --------------------------------------------------------------------------- #


def test_compose_appends_data_tool_rule_when_requested() -> None:
    prompt = compose_system_prompt(include_data_rule=True)
    assert prompt == f"{SYSTEM_PROMPT}\n\n{DATA_TOOL_RULE}"


def test_compose_include_data_rule_false_is_base_only() -> None:
    assert compose_system_prompt(include_data_rule=False) == SYSTEM_PROMPT


def test_compose_omits_data_tool_rule_by_default() -> None:
    assert DATA_TOOL_RULE not in compose_system_prompt()


def test_compose_orders_memory_rule_then_data_rule_then_block() -> None:
    memory_block = "Known facts about Rex:\n- age: 4 years"
    prompt = compose_system_prompt(
        memory_block=memory_block, include_memory_rule=True, include_data_rule=True
    )
    assert prompt == f"{SYSTEM_PROMPT}\n\n{MEMORY_WRITE_RULE}\n\n{DATA_TOOL_RULE}\n\n{memory_block}"


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

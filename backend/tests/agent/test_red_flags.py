"""Tests for the deterministic emergency red-flag detector.

`app.agent.red_flags` is pure logic — keyword/phrase matching with word
boundaries — so these run with no doubles, no graph, and no network. They cover
`detect_red_flags`, `has_red_flag`, the `RedFlag` model, and `EMERGENCY_BANNER`,
with special attention to word-boundary correctness and case-insensitivity.
"""

from __future__ import annotations

import pytest

from app.agent.red_flags import (
    EMERGENCY_BANNER,
    RED_FLAGS,
    RedFlag,
    detect_red_flags,
    has_red_flag,
)

# One representative phrase per RedFlag entry, mapped to its expected flag name.
REPRESENTATIVE_PHRASES: tuple[tuple[str, str], ...] = (
    ("My dog keeps vomiting and can't hold food down", "repeated_vomiting"),
    ("His belly looks bloated this evening", "bloated_abdomen"),
    ("My dog collapsed suddenly on the walk", "collapse"),
    ("My dog is having a seizure right now", "seizure"),
    ("Her gums are pale and she seems weak", "pale_gums"),
    ("He is having trouble breathing after playing", "breathing_difficulty"),
    ("I think she ate chocolate off the counter", "suspected_toxin"),
    ("There is blood in stool from my puppy", "blood_in_stool_or_vomit"),
    ("He has been unable to urinate all day", "unable_to_urinate"),
    ("Could this be heatstroke after the hot walk?", "heatstroke"),
)

# Every (flag name, phrase) pair declared in the module — the exhaustive check
# that each configured phrase actually triggers its own flag.
ALL_PHRASE_CASES: tuple[tuple[str, str], ...] = tuple(
    (red_flag.name, phrase) for red_flag in RED_FLAGS for phrase in red_flag.phrases
)


# --------------------------------------------------------------------------- #
# detect_red_flags — clean text
# --------------------------------------------------------------------------- #


def test_detect_red_flags_empty_for_clean_text() -> None:
    assert detect_red_flags("What is a good treat for training my puppy?") == []


def test_detect_red_flags_empty_for_empty_string() -> None:
    assert detect_red_flags("") == []


# --------------------------------------------------------------------------- #
# detect_red_flags — one representative phrase per flag
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("text", "expected_name"), REPRESENTATIVE_PHRASES)
def test_detect_red_flags_matches_representative_phrase(text: str, expected_name: str) -> None:
    assert detect_red_flags(text) == [expected_name]


@pytest.mark.parametrize(("text", "expected_name"), REPRESENTATIVE_PHRASES)
def test_has_red_flag_true_for_representative_phrase(text: str, expected_name: str) -> None:
    assert has_red_flag(text) is True


def test_representative_phrases_cover_every_flag() -> None:
    covered_names = {expected_name for _, expected_name in REPRESENTATIVE_PHRASES}
    declared_names = {red_flag.name for red_flag in RED_FLAGS}
    assert covered_names == declared_names


# --------------------------------------------------------------------------- #
# detect_red_flags — every configured phrase triggers its flag
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("expected_name", "phrase"), ALL_PHRASE_CASES)
def test_every_phrase_triggers_its_flag(expected_name: str, phrase: str) -> None:
    text = f"My dog {phrase} and I am worried."
    assert expected_name in detect_red_flags(text)
    assert has_red_flag(text) is True


# --------------------------------------------------------------------------- #
# Word-boundary correctness
# --------------------------------------------------------------------------- #


def test_blueberry_does_not_trip_pale_gums() -> None:
    assert detect_red_flags("Can my dog eat blueberry snacks?") == []
    assert has_red_flag("Can my dog eat blueberry snacks?") is False


def test_seizes_the_toy_does_not_trip_seizure() -> None:
    assert detect_red_flags("My dog seizes the toy and runs off") == []
    assert has_red_flag("My dog seizes the toy and runs off") is False


def test_seizure_word_is_detected() -> None:
    assert detect_red_flags("He had a seizure last night") == ["seizure"]


def test_seizing_word_is_detected() -> None:
    assert detect_red_flags("She is seizing right now") == ["seizure"]


def test_convulsion_word_is_detected() -> None:
    assert detect_red_flags("The dog had a convulsion") == ["seizure"]


def test_phrase_only_matches_on_whole_words() -> None:
    # "collapse" is a phrase, but "collapsible" should not word-boundary match it.
    assert detect_red_flags("I bought a collapsible dog crate") == []


# --------------------------------------------------------------------------- #
# Case-insensitivity
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    ["SEIZURE", "Seizure", "sEiZuRe", "my dog is having a SEIZURE"],
)
def test_matching_is_case_insensitive(text: str) -> None:
    assert detect_red_flags(text) == ["seizure"]
    assert has_red_flag(text) is True


def test_uppercase_multi_word_phrase_matches() -> None:
    assert detect_red_flags("HIS GUMS ARE PALE") == ["pale_gums"]


# --------------------------------------------------------------------------- #
# Multi-flag text
# --------------------------------------------------------------------------- #


def test_detect_red_flags_returns_multiple_names() -> None:
    text = "My dog had a seizure and now shows signs of heatstroke"
    result = detect_red_flags(text)
    assert set(result) == {"seizure", "heatstroke"}


def test_detect_red_flags_orders_by_declaration_not_text() -> None:
    # "heatstroke" appears first in the text, but "seizure" is declared earlier
    # in RED_FLAGS, so it comes first in the result.
    text = "Possible heatstroke, and then she had a seizure"
    assert detect_red_flags(text) == ["seizure", "heatstroke"]


def test_has_red_flag_true_when_any_of_many_matches() -> None:
    assert has_red_flag("Just a checkup question, but also she collapsed once") is True


# --------------------------------------------------------------------------- #
# Deduplication
# --------------------------------------------------------------------------- #


def test_detect_red_flags_dedupes_same_flag_from_multiple_phrases() -> None:
    # "collapse" and "unresponsive" are two phrases of the single "collapse" flag.
    text = "My dog will collapse and become unresponsive"
    assert detect_red_flags(text) == ["collapse"]


def test_detect_red_flags_dedupes_repeated_phrase() -> None:
    assert detect_red_flags("seizure seizure seizure") == ["seizure"]


# --------------------------------------------------------------------------- #
# has_red_flag — negative
# --------------------------------------------------------------------------- #


def test_has_red_flag_false_for_clean_text() -> None:
    assert has_red_flag("How much exercise does an Australian Shepherd need?") is False


def test_has_red_flag_false_for_empty_string() -> None:
    assert has_red_flag("") is False


# --------------------------------------------------------------------------- #
# RedFlag model
# --------------------------------------------------------------------------- #


def test_red_flag_is_pydantic_model_with_expected_fields() -> None:
    red_flag = RedFlag(name="example", phrases=("one", "two"))
    assert red_flag.name == "example"
    assert red_flag.phrases == ("one", "two")


def test_red_flag_serializes_to_dict() -> None:
    red_flag = RedFlag(name="example", phrases=("one",))
    assert red_flag.model_dump() == {"name": "example", "phrases": ("one",)}


def test_every_entry_is_a_red_flag_model() -> None:
    assert all(isinstance(red_flag, RedFlag) for red_flag in RED_FLAGS)


def test_red_flag_names_are_unique() -> None:
    names = [red_flag.name for red_flag in RED_FLAGS]
    assert len(names) == len(set(names))


def test_every_red_flag_has_at_least_one_phrase() -> None:
    assert all(len(red_flag.phrases) > 0 for red_flag in RED_FLAGS)


def test_expected_flag_names_present() -> None:
    expected = {
        "repeated_vomiting",
        "bloated_abdomen",
        "collapse",
        "seizure",
        "pale_gums",
        "breathing_difficulty",
        "suspected_toxin",
        "blood_in_stool_or_vomit",
        "unable_to_urinate",
        "heatstroke",
    }
    assert {red_flag.name for red_flag in RED_FLAGS} == expected


# --------------------------------------------------------------------------- #
# EMERGENCY_BANNER
# --------------------------------------------------------------------------- #


def test_emergency_banner_is_non_empty() -> None:
    assert EMERGENCY_BANNER.strip() != ""


def test_emergency_banner_mentions_veterinarian_and_emergency() -> None:
    lowered = EMERGENCY_BANNER.lower()
    assert "veterinarian" in lowered
    assert "emergency" in lowered

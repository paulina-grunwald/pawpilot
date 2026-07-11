"""Deterministic emergency red-flag detection (shared with the 012 eval suite).

A fast, keyword-based pre-check over the user's question. When any red flag
matches, the agent hard-prepends an emergency banner before the model's answer.
This is intentionally simple and high-recall; a full LLM verifier node is deferred
to 010b. Matching is phrase-based with word boundaries so "blueberry" does not
trip "blue gums" and "seizes the toy" does not trip "seizure".
"""

from __future__ import annotations

import re

from pydantic import BaseModel

EMERGENCY_BANNER = (
    "⚠️ This may be an emergency. Contact your veterinarian or the nearest "
    "emergency animal hospital right now. The guidance below is not a substitute "
    "for immediate professional care.\n\n"
)


class RedFlag(BaseModel):
    """A named emergency signal and the phrases that indicate it."""

    name: str
    phrases: tuple[str, ...]


RED_FLAGS: tuple[RedFlag, ...] = (
    RedFlag(
        name="repeated_vomiting",
        phrases=(
            "repeated vomiting",
            "keeps vomiting",
            "vomiting repeatedly",
            "won't stop vomiting",
            "cannot stop vomiting",
        ),
    ),
    RedFlag(
        name="bloated_abdomen",
        phrases=(
            "bloated",
            "distended abdomen",
            "hard abdomen",
            "swollen belly",
            "swollen stomach",
        ),
    ),
    RedFlag(
        name="collapse",
        phrases=("collapse", "collapsed", "unresponsive", "won't wake up", "passed out"),
    ),
    RedFlag(name="seizure", phrases=("seizure", "seizing", "seized", "convulsion", "convulsing")),
    RedFlag(
        name="pale_gums",
        phrases=(
            "blue gums",
            "white gums",
            "pale gums",
            "grey gums",
            "gums are blue",
            "gums are white",
            "gums are pale",
        ),
    ),
    RedFlag(
        name="breathing_difficulty",
        phrases=(
            "difficulty breathing",
            "trouble breathing",
            "struggling to breathe",
            "can't breathe",
            "cannot breathe",
            "labored breathing",
            "gasping for air",
            "choking",
        ),
    ),
    RedFlag(
        name="suspected_toxin",
        phrases=(
            "ate poison",
            "swallowed poison",
            "ingested poison",
            "ate rat bait",
            "ate antifreeze",
            "ate chocolate",
            "ate xylitol",
            "ate a toxin",
            "suspected poisoning",
        ),
    ),
    RedFlag(
        name="blood_in_stool_or_vomit",
        phrases=(
            "blood in stool",
            "blood in vomit",
            "blood in his stool",
            "blood in her stool",
            "bloody diarrhea",
            "bloody vomit",
            "vomiting blood",
        ),
    ),
    RedFlag(
        name="unable_to_urinate",
        phrases=(
            "unable to urinate",
            "can't urinate",
            "cannot urinate",
            "straining to urinate",
            "not urinating",
            "not urinated",
            "hasn't urinated",
            "haven't urinated",
        ),
    ),
    RedFlag(
        name="heatstroke", phrases=("heatstroke", "heat stroke", "overheating", "heat exhaustion")
    ),
)

_PHRASE_TO_FLAG: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE), red_flag.name)
    for red_flag in RED_FLAGS
    for phrase in red_flag.phrases
)


def detect_red_flags(text: str) -> list[str]:
    """Return the names of every red flag whose phrases appear in ``text``."""
    matched: list[str] = []
    for pattern, name in _PHRASE_TO_FLAG:
        if name not in matched and pattern.search(text):
            matched.append(name)
    return matched


def has_red_flag(text: str) -> bool:
    """True when the text contains any emergency red flag."""
    return any(pattern.search(text) for pattern, _ in _PHRASE_TO_FLAG)

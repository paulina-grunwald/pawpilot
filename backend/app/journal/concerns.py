from __future__ import annotations

from app.journal.schemas import (
    BathroomPayload,
    JournalEntryPayload,
    MedicationPayload,
    MoodPayload,
    SymptomPayload,
)

CONCERN_BRISTOL_THRESHOLD = 6
CONCERN_BATHROOM_COLORS = frozenset({"red", "black"})
CONCERN_MOOD_THRESHOLD = 2


def compute_is_concern(payload: JournalEntryPayload) -> bool:
    match payload:
        case SymptomPayload():
            return True
        case BathroomPayload(bristol_score=score) if (
            score is not None and score >= CONCERN_BRISTOL_THRESHOLD
        ):
            return True
        case BathroomPayload(color=color) if color in CONCERN_BATHROOM_COLORS:
            return True
        case MedicationPayload(missed_dose=True):
            return True
        case MoodPayload(score=score) if score <= CONCERN_MOOD_THRESHOLD:
            return True
        case _:
            return False

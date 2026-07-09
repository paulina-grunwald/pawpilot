from __future__ import annotations

from collections.abc import Callable

import pytest
from httpx import AsyncClient

from app.journal.concerns import compute_is_concern
from app.journal.schemas import (
    BathroomPayload,
    FreeNotePayload,
    MealPayload,
    MedicationPayload,
    MoodPayload,
    SymptomPayload,
    VetVisitPayload,
    WeightPayload,
)

EntryBuilder = Callable[..., dict[str, object]]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (SymptomPayload(severity=1, body_area=None), True),
        (SymptomPayload(severity=5, body_area="ears"), True),
        (BathroomPayload(kind="poop", bristol_score=5, color="brown"), False),
        (BathroomPayload(kind="poop", bristol_score=6, color="brown"), True),
        (BathroomPayload(kind="poop", bristol_score=7, color=None), True),
        (BathroomPayload(kind="poop", bristol_score=4, color="red"), True),
        (BathroomPayload(kind="poop", bristol_score=4, color="black"), True),
        (BathroomPayload(kind="poop", bristol_score=4, color="brown"), False),
        (BathroomPayload(kind="pee", bristol_score=None, color=None), False),
        (MedicationPayload(drug_name="Apoquel", dose="16 mg", missed_dose=True), True),
        (MedicationPayload(drug_name="Apoquel", dose="16 mg", missed_dose=False), False),
        (MoodPayload(score=1), True),
        (MoodPayload(score=2), True),
        (MoodPayload(score=3), False),
        (MealPayload(food_name="Kibble", category="kibble"), False),
        (WeightPayload(weight_grams=21400, source="vet"), False),
        (VetVisitPayload(reason="Annual exam"), False),
        (FreeNotePayload(text="Good day"), False),
    ],
)
def test_compute_is_concern_rule_matrix(
    payload: SymptomPayload
    | BathroomPayload
    | MedicationPayload
    | MoodPayload
    | MealPayload
    | WeightPayload
    | VetVisitPayload
    | FreeNotePayload,
    expected: bool,
) -> None:
    assert compute_is_concern(payload) is expected


async def test_created_entry_carries_derived_concern_flag(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    symptom = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry("symptom")
    )
    meal = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry("meal")
    )

    assert symptom.json()["is_concern"] is True
    assert meal.json()["is_concern"] is False


async def test_patch_recomputes_concern_flag(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry("bathroom")
    )
    entry_id = created.json()["id"]
    assert created.json()["is_concern"] is False

    escalated = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}",
        json={
            "payload": {
                "entry_type": "bathroom",
                "kind": "poop",
                "bristol_score": 6,
                "color": "brown",
            }
        },
    )
    assert escalated.json()["is_concern"] is True

    recovered = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}",
        json={
            "payload": {
                "entry_type": "bathroom",
                "kind": "poop",
                "bristol_score": 4,
                "color": "brown",
            }
        },
    )
    assert recovered.json()["is_concern"] is False

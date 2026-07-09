from __future__ import annotations

from collections.abc import Callable
from typing import cast

import pytest
from httpx import AsyncClient

EntryBuilder = Callable[..., dict[str, object]]


def _payload_override(
    valid_journal_entry: EntryBuilder, entry_type: str, **payload_overrides: object
) -> dict[str, object]:
    body = valid_journal_entry(entry_type)
    payload = dict(cast("dict[str, object]", body["payload"]))
    payload.update(payload_overrides)
    body["payload"] = payload
    return body


INVALID_PAYLOAD_CASES: list[tuple[str, dict[str, object]]] = [
    ("meal", {"food_name": ""}),
    ("meal", {"food_name": "x" * 201}),
    ("meal", {"amount_grams": 0}),
    ("meal", {"category": "raw"}),
    ("bathroom", {"kind": "pee", "bristol_score": 4, "color": None}),
    ("bathroom", {"kind": "pee", "bristol_score": None, "color": "brown"}),
    ("bathroom", {"bristol_score": 0}),
    ("bathroom", {"bristol_score": 8}),
    ("bathroom", {"color": "green"}),
    ("symptom", {"severity": 0}),
    ("symptom", {"severity": 6}),
    ("symptom", {"body_area": "wings"}),
    ("mood", {"score": 0}),
    ("mood", {"score": 6}),
    ("medication", {"drug_name": ""}),
    ("medication", {"dose": ""}),
    ("weight", {"weight_grams": 99}),
    ("weight", {"weight_grams": 120001}),
    ("weight", {"source": "guess"}),
    ("vet_visit", {"reason": ""}),
    ("vet_visit", {"reason": "x" * 501}),
    ("free_note", {"text": ""}),
    ("free_note", {"text": "x" * 2001}),
]


@pytest.mark.parametrize(("entry_type", "overrides"), INVALID_PAYLOAD_CASES)
async def test_invalid_payloads_are_rejected(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
    entry_type: str,
    overrides: dict[str, object],
) -> None:
    body = _payload_override(valid_journal_entry, entry_type, **overrides)

    response = await authenticated_client.post(f"/pets/{journal_pet['id']}/journal", json=body)

    assert response.status_code == 422, response.text


VALID_EDGE_CASES: list[tuple[str, dict[str, object]]] = [
    ("meal", {"brand": None, "amount_grams": None}),
    ("bathroom", {"kind": "both", "bristol_score": 7, "color": "red"}),
    ("bathroom", {"kind": "pee", "bristol_score": None, "color": None}),
    ("symptom", {"body_area": None}),
    ("weight", {"weight_grams": 100}),
    ("weight", {"weight_grams": 120000}),
    ("vet_visit", {"diagnosis": None, "follow_up": None, "vet_name": None}),
]


@pytest.mark.parametrize(("entry_type", "overrides"), VALID_EDGE_CASES)
async def test_valid_edge_payloads_are_accepted(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
    entry_type: str,
    overrides: dict[str, object],
) -> None:
    body = _payload_override(valid_journal_entry, entry_type, **overrides)

    response = await authenticated_client.post(f"/pets/{journal_pet['id']}/journal", json=body)

    assert response.status_code == 201, response.text


async def test_unknown_entry_type_is_rejected(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
) -> None:
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal",
        json={"payload": {"entry_type": "walk", "distance_km": 3}},
    )

    assert response.status_code == 422


async def test_symptom_without_tags_is_rejected(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal",
        json=valid_journal_entry("symptom", tags=[]),
    )

    assert response.status_code == 422


async def test_too_many_tags_are_rejected(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal",
        json=valid_journal_entry(tags=[f"tag-{index}" for index in range(21)]),
    )

    assert response.status_code == 422


async def test_overlong_tag_is_rejected(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal",
        json=valid_journal_entry(tags=["x" * 51]),
    )

    assert response.status_code == 422


async def test_overlong_note_is_rejected(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal",
        json=valid_journal_entry(note="x" * 1001),
    )

    assert response.status_code == 422


async def test_patch_rejects_explicit_null_payload(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]

    response = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}", json={"payload": None}
    )

    assert response.status_code == 422

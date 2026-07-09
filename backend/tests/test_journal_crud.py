from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from tests.conftest import JOURNAL_PAYLOAD_EXAMPLES

EntryBuilder = Callable[..., dict[str, object]]


@pytest.mark.parametrize("entry_type", sorted(JOURNAL_PAYLOAD_EXAMPLES))
async def test_create_entry_round_trips_every_type(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
    entry_type: str,
) -> None:
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry(entry_type)
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["entry_type"] == entry_type
    assert body["payload"] == JOURNAL_PAYLOAD_EXAMPLES[entry_type]
    assert body["pet_id"] == journal_pet["id"]
    assert isinstance(body["is_concern"], bool)
    assert body["photo_path"] is None
    assert body["photo_url"] is None


async def test_create_entry_defaults_occurred_at_to_now(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    before = datetime.now(UTC)
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    after = datetime.now(UTC)

    assert response.status_code == 201
    occurred_at = datetime.fromisoformat(response.json()["occurred_at"])
    assert before <= occurred_at <= after


async def test_create_entry_accepts_explicit_past_occurred_at(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    yesterday = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal",
        json=valid_journal_entry(occurred_at=yesterday),
    )

    assert response.status_code == 201
    assert datetime.fromisoformat(response.json()["occurred_at"]) == datetime.fromisoformat(
        yesterday
    )


async def test_create_entry_rejects_future_occurred_at(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    next_hour = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal",
        json=valid_journal_entry(occurred_at=next_hour),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "OCCURRED_AT_IN_FUTURE"


async def test_create_entry_rejects_occurred_at_before_birthday(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    response = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal",
        json=valid_journal_entry(occurred_at="2019-01-01T12:00:00+00:00"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "OCCURRED_AT_BEFORE_BIRTHDAY"


async def test_get_entry_returns_created_entry(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]

    response = await authenticated_client.get(f"/pets/{journal_pet['id']}/journal/{entry_id}")

    assert response.status_code == 200
    assert response.json()["id"] == entry_id


async def test_get_missing_entry_returns_404(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
) -> None:
    response = await authenticated_client.get(
        f"/pets/{journal_pet['id']}/journal/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "ENTRY_NOT_FOUND"


async def test_patch_updates_note_and_tags(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]

    response = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}",
        json={"note": "Ate everything", "tags": ["good-appetite"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["note"] == "Ate everything"
    assert body["tags"] == ["good-appetite"]
    assert body["payload"] == JOURNAL_PAYLOAD_EXAMPLES["meal"]


async def test_patch_replaces_payload_of_same_type(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]
    new_payload = {
        "entry_type": "meal",
        "food_name": "Boiled chicken",
        "brand": None,
        "amount_grams": 80,
        "category": "home_cooked",
    }

    response = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}", json={"payload": new_payload}
    )

    assert response.status_code == 200
    assert response.json()["payload"] == new_payload


async def test_patch_rejects_entry_type_change(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]

    response = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}",
        json={"payload": JOURNAL_PAYLOAD_EXAMPLES["mood"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "ENTRY_TYPE_IMMUTABLE"


async def test_patch_rejects_future_occurred_at(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]
    next_hour = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

    response = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}", json={"occurred_at": next_hour}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "OCCURRED_AT_IN_FUTURE"


async def test_patch_clearing_symptom_tags_is_rejected(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry("symptom")
    )
    entry_id = created.json()["id"]

    response = await authenticated_client.patch(
        f"/pets/{journal_pet['id']}/journal/{entry_id}", json={"tags": []}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "SYMPTOM_TAGS_REQUIRED"


async def test_delete_entry_removes_it(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry()
    )
    entry_id = created.json()["id"]

    delete_response = await authenticated_client.delete(
        f"/pets/{journal_pet['id']}/journal/{entry_id}"
    )
    get_response = await authenticated_client.get(f"/pets/{journal_pet['id']}/journal/{entry_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404

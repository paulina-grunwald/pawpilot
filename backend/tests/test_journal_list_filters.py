from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient

EntryBuilder = Callable[..., dict[str, object]]


def _hours_ago(hours: int) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


async def _seed(
    client: AsyncClient,
    pet_id: object,
    valid_journal_entry: EntryBuilder,
) -> dict[str, str]:
    seeds: dict[str, dict[str, object]] = {
        "old_meal": valid_journal_entry("meal", occurred_at=_hours_ago(72)),
        "recent_meal": valid_journal_entry(
            "meal", occurred_at=_hours_ago(2), note="Loved the new kibble"
        ),
        "symptom": valid_journal_entry("symptom", occurred_at=_hours_ago(5), tags=["limp", "Ears"]),
        "mood": valid_journal_entry("mood", occurred_at=_hours_ago(8)),
        "weight": valid_journal_entry("weight", occurred_at=_hours_ago(30)),
    }
    ids: dict[str, str] = {}
    for name, body in seeds.items():
        response = await client.post(f"/pets/{pet_id}/journal", json=body)
        assert response.status_code == 201, response.text
        ids[name] = response.json()["id"]
    return ids


async def _list(client: AsyncClient, pet_id: object, **params: object) -> dict[str, Any]:
    response = await client.get(f"/pets/{pet_id}/journal", params=params)  # type: ignore[arg-type]
    assert response.status_code == 200, response.text
    return dict(response.json())


async def test_list_returns_newest_first(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    ids = await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(authenticated_client, journal_pet["id"])

    assert [item["id"] for item in body["items"]] == [
        ids["recent_meal"],
        ids["symptom"],
        ids["mood"],
        ids["weight"],
        ids["old_meal"],
    ]
    assert body["total_matching"] == 5
    assert body["next_cursor"] is None


async def test_filter_by_single_entry_type(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    ids = await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(authenticated_client, journal_pet["id"], entry_type="meal")

    assert [item["id"] for item in body["items"]] == [ids["recent_meal"], ids["old_meal"]]
    assert body["total_matching"] == 2


async def test_filter_by_repeated_entry_type_is_or(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    response = await authenticated_client.get(
        f"/pets/{journal_pet['id']}/journal",
        params=[("entry_type", "mood"), ("entry_type", "weight")],
    )

    body = response.json()
    assert {item["entry_type"] for item in body["items"]} == {"mood", "weight"}
    assert body["total_matching"] == 2


async def test_filter_by_date_range(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    ids = await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(
        authenticated_client,
        journal_pet["id"],
        occurred_from=_hours_ago(24),
    )

    assert {item["id"] for item in body["items"]} == {
        ids["recent_meal"],
        ids["symptom"],
        ids["mood"],
    }
    assert body["total_matching"] == 3


async def test_filter_by_tag_overlap(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    ids = await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(authenticated_client, journal_pet["id"], tag="limp")

    assert [item["id"] for item in body["items"]] == [ids["symptom"]]
    assert body["total_matching"] == 1


async def test_filter_concerns_only(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    ids = await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(authenticated_client, journal_pet["id"], concerns_only=True)

    assert [item["id"] for item in body["items"]] == [ids["symptom"]]
    assert body["total_matching"] == 1


async def test_search_matches_note_case_insensitively(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    ids = await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(authenticated_client, journal_pet["id"], search="KIBBLE")

    assert [item["id"] for item in body["items"]] == [ids["recent_meal"]]


async def test_search_matches_tags_case_insensitively(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    ids = await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(authenticated_client, journal_pet["id"], search="ears")

    assert [item["id"] for item in body["items"]] == [ids["symptom"]]


async def test_search_does_not_match_payload_fields(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(authenticated_client, journal_pet["id"], search="Acana")

    assert body["items"] == []
    assert body["total_matching"] == 0


async def test_combined_filters_intersect(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    ids = await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(
        authenticated_client,
        journal_pet["id"],
        entry_type="symptom",
        occurred_from=_hours_ago(24),
        concerns_only=True,
        tag="limp",
    )

    assert [item["id"] for item in body["items"]] == [ids["symptom"]]
    assert body["total_matching"] == 1


async def test_total_matching_is_independent_of_limit(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    await _seed(authenticated_client, journal_pet["id"], valid_journal_entry)

    body = await _list(authenticated_client, journal_pet["id"], limit=2)

    assert len(body["items"]) == 2
    assert body["total_matching"] == 5
    assert body["next_cursor"] is not None

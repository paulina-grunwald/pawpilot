from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from httpx import AsyncClient

EntryBuilder = Callable[..., dict[str, object]]


async def _create_entries(
    client: AsyncClient,
    pet_id: object,
    valid_journal_entry: EntryBuilder,
    count: int,
    *,
    same_timestamp: bool = False,
) -> list[str]:
    base_time = datetime.now(UTC) - timedelta(hours=count + 1)
    ids: list[str] = []
    for index in range(count):
        occurred_at = base_time if same_timestamp else base_time + timedelta(hours=index)
        response = await client.post(
            f"/pets/{pet_id}/journal",
            json=valid_journal_entry(occurred_at=occurred_at.isoformat()),
        )
        assert response.status_code == 201, response.text
        ids.append(response.json()["id"])
    return ids


async def _walk_all_pages(
    client: AsyncClient, pet_id: object, limit: int, **extra: object
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, object] = {"limit": limit, **extra}
        if cursor is not None:
            params["cursor"] = cursor
        response = await client.get(f"/pets/{pet_id}/journal", params=params)  # type: ignore[arg-type]
        assert response.status_code == 200, response.text
        body = response.json()
        collected.extend(body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            return collected


async def test_pages_cover_all_entries_without_overlap(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created_ids = await _create_entries(
        authenticated_client, journal_pet["id"], valid_journal_entry, 5
    )

    items = await _walk_all_pages(authenticated_client, journal_pet["id"], limit=2)

    seen_ids = [item["id"] for item in items]
    assert len(seen_ids) == len(set(seen_ids)) == 5
    assert set(seen_ids) == set(created_ids)
    occurred_values = [item["occurred_at"] for item in items]
    assert occurred_values == sorted(occurred_values, reverse=True)


async def test_same_timestamp_entries_paginate_stably(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    created_ids = await _create_entries(
        authenticated_client,
        journal_pet["id"],
        valid_journal_entry,
        4,
        same_timestamp=True,
    )

    items = await _walk_all_pages(authenticated_client, journal_pet["id"], limit=1)

    seen_ids = [item["id"] for item in items]
    assert len(seen_ids) == len(set(seen_ids)) == 4
    assert set(seen_ids) == set(created_ids)


async def test_cursor_composes_with_filters(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
    valid_journal_entry: EntryBuilder,
) -> None:
    await _create_entries(authenticated_client, journal_pet["id"], valid_journal_entry, 3)
    mood = await authenticated_client.post(
        f"/pets/{journal_pet['id']}/journal", json=valid_journal_entry("mood")
    )
    assert mood.status_code == 201

    items = await _walk_all_pages(
        authenticated_client, journal_pet["id"], limit=1, entry_type="meal"
    )

    assert len(items) == 3
    assert all(item["entry_type"] == "meal" for item in items)


async def test_garbage_cursor_returns_400(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
) -> None:
    response = await authenticated_client.get(
        f"/pets/{journal_pet['id']}/journal", params={"cursor": "not-a-cursor"}
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "INVALID_CURSOR"


async def test_limit_is_bounded(
    authenticated_client: AsyncClient,
    journal_pet: dict[str, object],
) -> None:
    too_big = await authenticated_client.get(
        f"/pets/{journal_pet['id']}/journal", params={"limit": 101}
    )
    too_small = await authenticated_client.get(
        f"/pets/{journal_pet['id']}/journal", params={"limit": 0}
    )

    assert too_big.status_code == 422
    assert too_small.status_code == 422

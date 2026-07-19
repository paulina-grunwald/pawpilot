"""DB-backed tests for the metric reads in ``tractive.read_service``.

A pet is created over HTTP (so it is owned and visible on the shared test
connection), rollups are inserted directly, and the metric reads are called
against the same session so the unit conversion is checked against known inputs.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tractive.models import TractiveDayRollup
from app.integrations.tractive.read_service import (
    TractivePetDataReader,
    fetch_metric_on_date,
    fetch_metric_window,
)


async def _create_pet(
    client: AsyncClient, valid_pet_payload: Callable[..., dict[str, object]]
) -> uuid.UUID:
    response = await client.post("/pets", json=valid_pet_payload())
    assert response.status_code == 201, response.text
    return uuid.UUID(str(response.json()["id"]))


async def _insert_rollups(
    session: AsyncSession,
    pet_id: uuid.UUID,
    days: list[tuple[date, float, float]],
) -> None:
    """Insert ``(date, night_minutes, day_minutes)`` rollups for ``pet_id``."""
    session.add_all(
        TractiveDayRollup(
            pet_id=pet_id,
            date=day,
            minutes_night_sleep=night_minutes,
            minutes_day_sleep=day_minutes,
            source="gdpr_export",
        )
        for day, night_minutes, day_minutes in days
    )
    await session.flush()


# --------------------------------------------------------------------------- #
# fetch_metric_window
# --------------------------------------------------------------------------- #


async def test_window_is_empty_when_no_rollups(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)

    rows = await fetch_metric_window(db_session, pet_id, days=7)

    assert rows == []


async def test_window_converts_minutes_to_hours_and_sums_total_sleep(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 420.0, 120.0)])

    rows = await fetch_metric_window(db_session, pet_id, days=7)

    assert len(rows) == 1
    assert rows[0].night_sleep_hours == 7.0
    assert rows[0].day_sleep_hours == 2.0
    assert rows[0].total_sleep_hours == 9.0


async def test_window_returns_days_oldest_first(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(
        db_session,
        pet_id,
        [
            (date(2024, 5, 16), 480.0, 0.0),
            (date(2024, 5, 14), 360.0, 120.0),
            (date(2024, 5, 15), 420.0, 120.0),
        ],
    )

    rows = await fetch_metric_window(db_session, pet_id, days=7)

    assert [row.date for row in rows] == [
        date(2024, 5, 14),
        date(2024, 5, 15),
        date(2024, 5, 16),
    ]


async def test_window_limits_to_the_most_recent_days(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(
        db_session,
        pet_id,
        [
            (date(2024, 5, 14), 360.0, 120.0),
            (date(2024, 5, 15), 420.0, 120.0),
            (date(2024, 5, 16), 480.0, 0.0),
        ],
    )

    rows = await fetch_metric_window(db_session, pet_id, days=2)

    assert [row.date for row in rows] == [date(2024, 5, 15), date(2024, 5, 16)]


async def test_window_rounds_hours_to_two_decimals(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 100.0, 0.0)])

    rows = await fetch_metric_window(db_session, pet_id, days=7)

    assert rows[0].night_sleep_hours == 1.67
    assert rows[0].total_sleep_hours == 1.67


async def test_window_ignores_other_pets(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    """The tool cannot widen its scope, so the query must never cross pets."""
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    other_pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, other_pet_id, [(date(2024, 5, 22), 600.0, 0.0)])

    rows = await fetch_metric_window(db_session, pet_id, days=7)

    assert rows == []


# --------------------------------------------------------------------------- #
# fetch_metric_on_date
# --------------------------------------------------------------------------- #


async def test_on_date_returns_that_days_row(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(
        db_session,
        pet_id,
        [(date(2024, 5, 21), 300.0, 60.0), (date(2024, 5, 22), 420.0, 120.0)],
    )

    row = await fetch_metric_on_date(db_session, pet_id, date(2024, 5, 22))

    assert row is not None
    assert row.date == date(2024, 5, 22)
    assert row.total_sleep_hours == 9.0


async def test_on_date_returns_none_when_day_missing(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 420.0, 120.0)])

    assert await fetch_metric_on_date(db_session, pet_id, date(2024, 5, 23)) is None


async def test_on_date_ignores_other_pets(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    other_pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, other_pet_id, [(date(2024, 5, 22), 600.0, 0.0)])

    assert await fetch_metric_on_date(db_session, pet_id, date(2024, 5, 22)) is None


async def test_defaults_are_zero_not_null_for_the_new_rollup_columns(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    """A rollup written before the sleep/outing columns existed still reads cleanly."""
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 420.0, 120.0)])

    row = await fetch_metric_on_date(db_session, pet_id, date(2024, 5, 22))

    assert row is not None
    assert row.sleep_bout_count == 0
    assert row.outings_count == 0
    assert row.outings_total_hours == 0.0
    assert row.walking_distance_km == 0.0
    assert row.sleep_fragmentation_index is None
    assert row.resting_heart_rate_bpm is None


# --------------------------------------------------------------------------- #
# TractivePetDataReader
# --------------------------------------------------------------------------- #


async def test_reader_delegates_to_fetch_window(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 420.0, 120.0)])

    reader = TractivePetDataReader(db_session, pet_id)

    assert await reader.fetch_window(7) == await fetch_metric_window(db_session, pet_id, days=7)


async def test_reader_delegates_to_fetch_on_date(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 420.0, 120.0)])

    reader = TractivePetDataReader(db_session, pet_id)
    via_reader = await reader.fetch_on_date(date(2024, 5, 22))
    direct = await fetch_metric_on_date(db_session, pet_id, date(2024, 5, 22))

    assert via_reader == direct


async def test_reader_is_scoped_to_its_pet(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    """The reader binds the pet, so no argument the model picks can reach another."""
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    other_pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, other_pet_id, [(date(2024, 5, 22), 600.0, 0.0)])

    reader = TractivePetDataReader(db_session, pet_id)

    assert await reader.fetch_window(365) == []
    assert await reader.fetch_on_date(date(2024, 5, 22)) is None

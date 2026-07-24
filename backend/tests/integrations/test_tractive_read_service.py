"""DB-backed tests for the sleep aggregation in ``tractive.read_service``.

A pet is created over HTTP (so it is owned and visible on the shared test
connection), rollups are inserted directly, and `summarize_sleep` is called
against the same session so the averaging is checked against known inputs.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tractive.models import TractiveDayRollup
from app.integrations.tractive.read_service import (
    TractiveSleepReader,
    sleep_on_date,
    summarize_sleep,
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
# summarize_sleep
# --------------------------------------------------------------------------- #


async def test_summarize_sleep_returns_empty_summary_when_no_rollups(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)

    summary = await summarize_sleep(db_session, pet_id, days=7)

    assert summary.days_requested == 7
    assert summary.days_with_data == 0
    assert summary.average_total_sleep_hours is None
    assert summary.average_night_sleep_hours is None
    assert summary.average_day_sleep_hours is None
    assert summary.start_date is None
    assert summary.end_date is None


async def test_summarize_sleep_averages_over_all_days_in_window(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(
        db_session,
        pet_id,
        [
            (date(2024, 5, 14), 360.0, 60.0),  # 6h night + 1h day = 7h
            (date(2024, 5, 15), 420.0, 120.0),  # 7h night + 2h day = 9h
            (date(2024, 5, 16), 480.0, 0.0),  # 8h night + 0h day = 8h
        ],
    )

    summary = await summarize_sleep(db_session, pet_id, days=7)

    assert summary.days_requested == 7
    assert summary.days_with_data == 3
    assert summary.average_night_sleep_hours == 7.0
    assert summary.average_day_sleep_hours == 1.0
    assert summary.average_total_sleep_hours == 8.0
    assert summary.start_date == date(2024, 5, 14)
    assert summary.end_date == date(2024, 5, 16)


async def test_summarize_sleep_limits_to_most_recent_days(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(
        db_session,
        pet_id,
        [
            (date(2024, 5, 14), 360.0, 60.0),  # excluded by days=2
            (date(2024, 5, 15), 420.0, 120.0),
            (date(2024, 5, 16), 480.0, 0.0),
        ],
    )

    summary = await summarize_sleep(db_session, pet_id, days=2)

    assert summary.days_with_data == 2
    assert summary.average_night_sleep_hours == 7.5  # (420 + 480) / 2 = 450min
    assert summary.average_day_sleep_hours == 1.0  # (120 + 0) / 2 = 60min
    assert summary.average_total_sleep_hours == 8.5  # (540 + 480) / 2 = 510min
    assert summary.start_date == date(2024, 5, 15)
    assert summary.end_date == date(2024, 5, 16)


async def test_summarize_sleep_rounds_hours_to_two_decimals(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 16), 100.0, 0.0)])

    summary = await summarize_sleep(db_session, pet_id, days=7)

    # 100 minutes / 60 = 1.6666... -> rounded to 2dp.
    assert summary.average_night_sleep_hours == 1.67
    assert summary.average_total_sleep_hours == 1.67


async def test_summarize_sleep_ignores_other_pets(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    other_pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, other_pet_id, [(date(2024, 5, 16), 480.0, 0.0)])

    summary = await summarize_sleep(db_session, pet_id, days=7)

    assert summary.days_with_data == 0


# sleep_on_date
async def test_sleep_on_date_returns_that_days_hours(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(
        db_session,
        pet_id,
        [
            (date(2024, 5, 21), 360.0, 60.0),  # neighbour day, must be ignored
            (date(2024, 5, 22), 420.0, 120.0),  # 7h night + 2h day = 9h total
        ],
    )

    daily = await sleep_on_date(db_session, pet_id, date(2024, 5, 22))

    assert daily.date == date(2024, 5, 22)
    assert daily.has_data is True
    assert daily.night_sleep_hours == 7.0
    assert daily.day_sleep_hours == 2.0
    assert daily.total_sleep_hours == 9.0


async def test_sleep_on_date_marks_no_data_when_day_missing(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 420.0, 120.0)])

    daily = await sleep_on_date(db_session, pet_id, date(2024, 5, 23))

    assert daily.date == date(2024, 5, 23)
    assert daily.has_data is False
    assert daily.night_sleep_hours is None
    assert daily.day_sleep_hours is None
    assert daily.total_sleep_hours is None


async def test_sleep_on_date_rounds_hours_to_two_decimals(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 100.0, 0.0)])

    daily = await sleep_on_date(db_session, pet_id, date(2024, 5, 22))

    # 100 minutes / 60 = 1.6666... -> rounded to 2dp.
    assert daily.night_sleep_hours == 1.67
    assert daily.total_sleep_hours == 1.67


async def test_sleep_on_date_ignores_other_pets(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    other_pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, other_pet_id, [(date(2024, 5, 22), 480.0, 0.0)])

    daily = await sleep_on_date(db_session, pet_id, date(2024, 5, 22))

    assert daily.has_data is False


# --------------------------------------------------------------------------- #
# TractiveSleepReader
# --------------------------------------------------------------------------- #


async def test_reader_delegates_to_summarize_sleep(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 16), 480.0, 0.0)])

    reader = TractiveSleepReader(db_session, pet_id)
    via_reader = await reader.summarize_sleep(7)
    direct = await summarize_sleep(db_session, pet_id, days=7)

    assert via_reader == direct


async def test_reader_delegates_to_sleep_on_date(
    authenticated_client: AsyncClient,
    db_session: AsyncSession,
    valid_pet_payload: Callable[..., dict[str, object]],
) -> None:
    pet_id = await _create_pet(authenticated_client, valid_pet_payload)
    await _insert_rollups(db_session, pet_id, [(date(2024, 5, 22), 480.0, 0.0)])

    reader = TractiveSleepReader(db_session, pet_id)
    via_reader = await reader.sleep_on_date(date(2024, 5, 22))
    direct = await sleep_on_date(db_session, pet_id, date(2024, 5, 22))

    assert via_reader == direct

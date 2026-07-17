"""Tests for TractiveIngestService persistence behavior."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.integrations.tractive.consolidate import GdprExportPayloads
from app.integrations.tractive.models import TractiveDayRollup, TractiveRawPayload
from app.integrations.tractive.schemas import TractivePayloadType, TractiveSource
from app.integrations.tractive.service import TractiveIngestService
from app.pets.models import Pet


@pytest_asyncio.fixture
async def pet_id(db_session: AsyncSession) -> uuid.UUID:
    """Insert a user + pet directly via the session and return the pet's id."""
    user = User(
        email="ingest@example.com",
        hashed_password="not-a-real-hash",
        is_active=True,
        is_superuser=False,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    pet = Pet(
        owner_user_id=user.id,
        name="Luna",
        birthday=date(2021, 6, 14),
        sex="female",
        spayed_neutered=True,
        weight_grams=22000,
    )
    db_session.add(pet)
    await db_session.flush()
    return pet.id


async def test_ingest_refreshes_ingested_at_on_re_ingest(
    db_session: AsyncSession,
    pet_id: uuid.UUID,
    sample_gdpr_payloads: GdprExportPayloads,
) -> None:
    service = TractiveIngestService(db_session)

    async def read_ingested_at() -> datetime:
        value = await db_session.scalar(
            select(TractiveDayRollup.ingested_at).where(
                TractiveDayRollup.pet_id == pet_id,
                TractiveDayRollup.date == date(2024, 5, 15),
            )
        )
        assert value is not None
        return value

    await service.ingest_gdpr_export(pet_id, sample_gdpr_payloads)
    first_ingested_at = await read_ingested_at()

    await service.ingest_gdpr_export(pet_id, sample_gdpr_payloads)
    second_ingested_at = await read_ingested_at()

    assert second_ingested_at > first_ingested_at


async def test_ingest_gdpr_export_persists_rollups_and_raw_payloads(
    db_session: AsyncSession,
    pet_id: uuid.UUID,
    sample_gdpr_payloads: GdprExportPayloads,
) -> None:
    service = TractiveIngestService(db_session)

    result = await service.ingest_gdpr_export(pet_id, sample_gdpr_payloads)

    assert result.rollups_upserted == 2
    assert result.raw_payloads_stored == 5
    assert result.date_range_start == date(2024, 5, 15)
    assert result.date_range_end == date(2024, 5, 16)

    rollup_count = await db_session.scalar(
        select(func.count())
        .select_from(TractiveDayRollup)
        .where(TractiveDayRollup.pet_id == pet_id)
    )
    assert rollup_count == 2

    raw_count = await db_session.scalar(
        select(func.count())
        .select_from(TractiveRawPayload)
        .where(TractiveRawPayload.pet_id == pet_id)
    )
    assert raw_count == 5

    # All five payload types present, all stamped with the same batch id.
    raw_rows = (
        (
            await db_session.execute(
                select(TractiveRawPayload).where(TractiveRawPayload.pet_id == pet_id)
            )
        )
        .scalars()
        .all()
    )
    assert {row.payload_type for row in raw_rows} == {item.value for item in TractivePayloadType}
    assert {row.ingest_batch_id for row in raw_rows} == {result.ingest_batch_id}
    assert all(row.source == TractiveSource.GDPR_EXPORT.value for row in raw_rows)


async def test_ingest_persists_expected_rollup_columns(
    db_session: AsyncSession,
    pet_id: uuid.UUID,
    sample_gdpr_payloads: GdprExportPayloads,
) -> None:
    service = TractiveIngestService(db_session)
    await service.ingest_gdpr_export(pet_id, sample_gdpr_payloads)

    day_one = await db_session.scalar(
        select(TractiveDayRollup).where(
            TractiveDayRollup.pet_id == pet_id,
            TractiveDayRollup.date == date(2024, 5, 15),
        )
    )
    assert day_one is not None
    assert day_one.minutes_night_sleep == 60.0
    assert day_one.minutes_active == 30.0
    assert day_one.heart_rate_n_samples == 3
    assert day_one.heart_rate_mean == 62.0
    assert day_one.gps_count == 3
    assert day_one.gps_segments_counted == 1
    assert day_one.battery_min == 60
    assert day_one.battery_max == 80
    assert day_one.n_charging_starts == 1
    assert day_one.source == TractiveSource.GDPR_EXPORT.value
    # Hourly bucket keys round-trip as strings through JSONB.
    assert "0" in day_one.hourly_minutes_by_category
    assert day_one.hourly_minutes_by_category["0"]["night_sleep"] == 60.0


async def test_re_ingest_upserts_rollups_and_appends_raw_payloads(
    db_session: AsyncSession,
    pet_id: uuid.UUID,
    sample_gdpr_payloads: GdprExportPayloads,
) -> None:
    service = TractiveIngestService(db_session)
    first_result = await service.ingest_gdpr_export(pet_id, sample_gdpr_payloads)
    second_result = await service.ingest_gdpr_export(pet_id, sample_gdpr_payloads)

    assert first_result.ingest_batch_id != second_result.ingest_batch_id

    rollup_count = await db_session.scalar(
        select(func.count())
        .select_from(TractiveDayRollup)
        .where(TractiveDayRollup.pet_id == pet_id)
    )
    assert rollup_count == 2  # upsert, not duplicate

    raw_count = await db_session.scalar(
        select(func.count())
        .select_from(TractiveRawPayload)
        .where(TractiveRawPayload.pet_id == pet_id)
    )
    assert raw_count == 10  # both batches kept

    distinct_batches = await db_session.scalars(
        select(TractiveRawPayload.ingest_batch_id)
        .where(TractiveRawPayload.pet_id == pet_id)
        .distinct()
    )
    assert set(distinct_batches.all()) == {
        first_result.ingest_batch_id,
        second_result.ingest_batch_id,
    }


async def test_ingest_empty_export_stores_raw_payloads_but_no_rollups(
    db_session: AsyncSession, pet_id: uuid.UUID
) -> None:
    empty_payloads = GdprExportPayloads(
        activity_data=[],
        position_reports=[],
        hardware_reports=[],
        resting_heart_rates=[],
        resting_respiratory_rates=[],
    )
    service = TractiveIngestService(db_session)
    result = await service.ingest_gdpr_export(pet_id, empty_payloads)

    assert result.rollups_upserted == 0
    assert result.raw_payloads_stored == 5
    assert result.date_range_start is None
    assert result.date_range_end is None

    rollup_count = await db_session.scalar(
        select(func.count())
        .select_from(TractiveDayRollup)
        .where(TractiveDayRollup.pet_id == pet_id)
    )
    assert rollup_count == 0

    raw_count = await db_session.scalar(
        select(func.count())
        .select_from(TractiveRawPayload)
        .where(TractiveRawPayload.pet_id == pet_id)
    )
    assert raw_count == 5

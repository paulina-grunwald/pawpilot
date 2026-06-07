"""Persistence service for Tractive ingestion.

Takes computed rollups + raw payload blobs and writes them to the DB:
  * Rollups: upserted on ``(pet_id, date)`` so re-ingesting overwrites in place.
  * Raw payloads: append-only, grouped by a single ``ingest_batch_id`` per
    call so we can identify which fetch a blob came from.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tractive.consolidate import GdprExportPayloads, build_per_day
from app.integrations.tractive.models import TractiveDayRollup, TractiveRawPayload
from app.integrations.tractive.schemas import (
    PerDayRollup,
    TractivePayloadType,
    TractiveSource,
)


class IngestResult(BaseModel):
    """Summary returned to callers after an ingest run."""

    ingest_batch_id: uuid.UUID
    rollups_upserted: int
    raw_payloads_stored: int
    date_range_start: date_type | None
    date_range_end: date_type | None


_ROLLUP_UPDATABLE_COLUMNS = (
    "minutes_active",
    "minutes_low_intensity",
    "minutes_moderate",
    "minutes_night_sleep",
    "minutes_day_sleep",
    "minutes_no_signal",
    "hourly_minutes_by_category",
    "heart_rate_n_samples",
    "heart_rate_mean",
    "heart_rate_min",
    "heart_rate_max",
    "heart_rate_samples",
    "respiratory_rate_n_samples",
    "respiratory_rate_mean",
    "respiratory_rate_min",
    "respiratory_rate_max",
    "respiratory_rate_samples",
    "gps_count",
    "gps_distance_km",
    "gps_segments_counted",
    "gps_segments_dropped",
    "gps_by_sensor",
    "gps_first_time",
    "gps_last_time",
    "battery_min",
    "battery_max",
    "temperature_min",
    "temperature_max",
    "n_charging_starts",
    "source",
    "ingested_at",
)


class TractiveIngestService:
    """Service for persisting Tractive data into ``tractive_day_rollup`` +
    ``tractive_raw_payload``.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ingest_gdpr_export(
        self, pet_id: uuid.UUID, payloads: GdprExportPayloads
    ) -> IngestResult:
        """Consolidate + persist a full GDPR export for one pet.

        Generates one ``ingest_batch_id`` for the whole call. The raw blobs are
        stored as-is so the rollup can be re-derived if consolidation logic
        changes. Rollups are upserted on ``(pet_id, date)``.
        """
        rollups = build_per_day(payloads)
        ingest_batch_id = uuid.uuid4()

        date_range_start = rollups[0].date if rollups else None
        date_range_end = rollups[-1].date if rollups else None

        await self._persist_raw_payloads(
            pet_id=pet_id,
            payloads=payloads,
            source=TractiveSource.GDPR_EXPORT,
            ingest_batch_id=ingest_batch_id,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )
        await self._upsert_rollups(
            pet_id=pet_id,
            rollups=rollups,
            source=TractiveSource.GDPR_EXPORT,
        )

        return IngestResult(
            ingest_batch_id=ingest_batch_id,
            rollups_upserted=len(rollups),
            raw_payloads_stored=len(_RAW_PAYLOAD_FIELDS),
            date_range_start=date_range_start,
            date_range_end=date_range_end,
        )

    async def reprocess_latest_batch(self, pet_id: uuid.UUID) -> IngestResult:
        """Re-derive rollups from the most recent stored raw batch.

        Useful when the consolidation logic changes (e.g. category mapping
        updates) — saves the user from re-uploading their GDPR zip.

        Returns an ``IngestResult`` with ``raw_payloads_stored=0`` because the
        raw blobs are read, not written.
        """
        batch_id, batch_rows = await self._latest_raw_batch(pet_id)
        if batch_id is None:
            return IngestResult(
                ingest_batch_id=uuid.uuid4(),
                rollups_upserted=0,
                raw_payloads_stored=0,
                date_range_start=None,
                date_range_end=None,
            )

        payloads_kwargs: dict[str, list[dict[str, object]]] = {
            field_name: [] for field_name, _ in _RAW_PAYLOAD_FIELDS
        }
        payload_type_to_field = {
            payload_type.value: field_name for field_name, payload_type in _RAW_PAYLOAD_FIELDS
        }
        for row in batch_rows:
            field = payload_type_to_field.get(row.payload_type)
            if field is not None:
                payloads_kwargs[field] = row.payload
        payloads = GdprExportPayloads(**payloads_kwargs)

        rollups = build_per_day(payloads)
        await self._upsert_rollups(
            pet_id=pet_id,
            rollups=rollups,
            source=TractiveSource(batch_rows[0].source),
        )

        return IngestResult(
            ingest_batch_id=batch_id,
            rollups_upserted=len(rollups),
            raw_payloads_stored=0,
            date_range_start=rollups[0].date if rollups else None,
            date_range_end=rollups[-1].date if rollups else None,
        )

    async def _latest_raw_batch(
        self, pet_id: uuid.UUID
    ) -> tuple[uuid.UUID | None, list[TractiveRawPayload]]:
        latest_batch_query = (
            select(TractiveRawPayload.ingest_batch_id)
            .where(TractiveRawPayload.pet_id == pet_id)
            .order_by(TractiveRawPayload.fetched_at.desc())
            .limit(1)
        )
        batch_id = (await self._session.execute(latest_batch_query)).scalar_one_or_none()
        if batch_id is None:
            return None, []
        rows_query = select(TractiveRawPayload).where(
            TractiveRawPayload.pet_id == pet_id,
            TractiveRawPayload.ingest_batch_id == batch_id,
        )
        rows = list((await self._session.execute(rows_query)).scalars().all())
        return batch_id, rows

    async def _persist_raw_payloads(
        self,
        *,
        pet_id: uuid.UUID,
        payloads: GdprExportPayloads,
        source: TractiveSource,
        ingest_batch_id: uuid.UUID,
        date_range_start: date_type | None,
        date_range_end: date_type | None,
    ) -> None:
        rows = [
            TractiveRawPayload(
                pet_id=pet_id,
                payload_type=payload_type.value,
                source=source.value,
                date_range_start=date_range_start,
                date_range_end=date_range_end,
                payload=getattr(payloads, field_name),
                ingest_batch_id=ingest_batch_id,
            )
            for field_name, payload_type in _RAW_PAYLOAD_FIELDS
        ]
        self._session.add_all(rows)
        await self._session.flush()

    async def _upsert_rollups(
        self,
        *,
        pet_id: uuid.UUID,
        rollups: list[PerDayRollup],
        source: TractiveSource,
    ) -> None:
        if not rollups:
            return
        values = [_rollup_to_row(pet_id, rollup, source) for rollup in rollups]
        statement = postgres_insert(TractiveDayRollup).values(values)
        statement = statement.on_conflict_do_update(
            index_elements=["pet_id", "date"],
            set_={column: statement.excluded[column] for column in _ROLLUP_UPDATABLE_COLUMNS},
        )
        await self._session.execute(statement)
        await self._session.flush()


_RAW_PAYLOAD_FIELDS: tuple[tuple[str, TractivePayloadType], ...] = (
    ("activity_data", TractivePayloadType.ACTIVITY_DATA),
    ("position_reports", TractivePayloadType.POSITION_REPORTS),
    ("hardware_reports", TractivePayloadType.HARDWARE_REPORTS),
    ("resting_heart_rates", TractivePayloadType.RESTING_HEART_RATES),
    ("resting_respiratory_rates", TractivePayloadType.RESTING_RESPIRATORY_RATES),
)


def _rollup_to_row(
    pet_id: uuid.UUID, rollup: PerDayRollup, source: TractiveSource
) -> dict[str, Any]:
    """Flatten a PerDayRollup into the column dict expected by INSERT."""
    minutes = rollup.minutes
    heart_rate = rollup.resting_heart_rate
    respiratory_rate = rollup.resting_respiratory_rate
    positions = rollup.positions
    tracker = rollup.tracker
    return {
        "pet_id": pet_id,
        "date": rollup.date,
        "minutes_active": minutes.active,
        "minutes_low_intensity": minutes.low_intensity,
        "minutes_moderate": minutes.moderate,
        "minutes_night_sleep": minutes.night_sleep,
        "minutes_day_sleep": minutes.day_sleep,
        "minutes_no_signal": minutes.no_signal,
        # JSONB keys round-trip as strings — int hour keys are coerced on write.
        "hourly_minutes_by_category": {
            str(hour): per_label for hour, per_label in rollup.hourly_minutes_by_category.items()
        },
        "heart_rate_n_samples": heart_rate.n_samples,
        "heart_rate_mean": heart_rate.mean,
        "heart_rate_min": heart_rate.min,
        "heart_rate_max": heart_rate.max,
        "heart_rate_samples": heart_rate.samples,
        "respiratory_rate_n_samples": respiratory_rate.n_samples,
        "respiratory_rate_mean": respiratory_rate.mean,
        "respiratory_rate_min": respiratory_rate.min,
        "respiratory_rate_max": respiratory_rate.max,
        "respiratory_rate_samples": respiratory_rate.samples,
        "gps_count": positions.count,
        "gps_distance_km": positions.distance_km,
        "gps_segments_counted": positions.segments_counted,
        "gps_segments_dropped": positions.segments_dropped,
        "gps_by_sensor": positions.by_sensor,
        "gps_first_time": positions.first_time,
        "gps_last_time": positions.last_time,
        "battery_min": tracker.battery_min,
        "battery_max": tracker.battery_max,
        "temperature_min": tracker.temperature_min,
        "temperature_max": tracker.temperature_max,
        "n_charging_starts": tracker.n_charging_starts,
        "source": source.value,
    }

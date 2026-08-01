"""SQLAlchemy models for Tractive ingestion: processed rollup + raw audit blobs."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TractiveDayRollup(Base):
    """One processed day of Tractive data per pet.

    Populated by the consolidation pipeline from one or more raw payloads.
    Upserted on `(pet_id, date)` — re-ingesting the same day overwrites.
    """

    __tablename__ = "tractive_day_rollup"
    __table_args__ = (
        UniqueConstraint("pet_id", "date", name="uq_tractive_day_rollup_pet_date"),
        CheckConstraint(
            "source in ('gdpr_export', 'live_api')",
            name="ck_tractive_day_rollup_source_enum",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pet_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)

    minutes_active: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    minutes_low_intensity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    minutes_moderate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    minutes_night_sleep: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    minutes_day_sleep: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    minutes_no_signal: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hourly_minutes_by_category: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    heart_rate_n_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heart_rate_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate_samples: Mapped[list[float]] = mapped_column(JSONB, nullable=False, default=list)

    respiratory_rate_n_samples: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    respiratory_rate_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate_samples: Mapped[list[float]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # Record-level daily vitals: one measurement event counts once, motion
    # contaminated bursts rejected. See consolidate.record_stats_from_records.
    heart_rate_record_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    heart_rate_record_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate_ci95_half_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate_record_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    respiratory_rate_record_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate_ci95_half_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate_night_record_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    respiratory_rate_night_record_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    respiratory_rate_day_record_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    respiratory_rate_day_record_mean: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Sleep continuity from the activity timeline: consolidated bouts, never
    # clinical stages. Fragmentation is awake interruptions per hour of rest.
    sleep_longest_bout_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_bout_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_fragmentation_index: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Outings derived from GPS against a data-derived home (the configured
    # geofence can be stale). Counts are a floor, not an exact tally.
    outings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outings_total_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    outings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    home_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    gps_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gps_distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    gps_segments_counted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gps_segments_dropped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gps_by_sensor: Mapped[dict[str, int]] = mapped_column(JSONB, nullable=False, default=dict)
    gps_first_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gps_last_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    battery_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    battery_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_charging_starts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    source: Mapped[str] = mapped_column(String(20), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )


class TractiveRawPayload(Base):
    """Append-only audit table of raw Tractive payloads.

    Lets us re-run the consolidation pipeline if its logic changes (e.g. we
    learn what activity categories 0 and 1 really mean) without re-fetching
    from Tractive — important because the GDPR export is a manual one-shot.
    """

    __tablename__ = "tractive_raw_payload"
    __table_args__ = (
        CheckConstraint(
            "source in ('gdpr_export', 'live_api')",
            name="ck_tractive_raw_payload_source_enum",
        ),
        CheckConstraint(
            "payload_type in ("
            "'activity_data', 'position_reports', 'hardware_reports', "
            "'resting_heart_rates', 'resting_respiratory_rates'"
            ")",
            name="ck_tractive_raw_payload_type_enum",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    pet_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("pets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    date_range_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_range_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    payload: Mapped[Any] = mapped_column(JSONB, nullable=False)
    ingest_batch_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

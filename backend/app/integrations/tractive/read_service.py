"""Read-side queries against ``tractive_day_rollup`` for dashboard display."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tractive.models import TractiveDayRollup
from app.integrations.tractive.schemas import OutingDetail


class TractiveDailySummary(BaseModel):
    """One day's slim summary — just what the dashboard tiles need.

    Sample arrays and tracker hardware fields are deliberately omitted; the
    dashboard doesn't need them and they bloat the response.
    """

    date: date_type
    minutes_active: float
    minutes_low_intensity: float
    minutes_moderate: float
    minutes_night_sleep: float
    minutes_day_sleep: float
    minutes_no_signal: float
    hourly_minutes_by_category: dict[int, dict[str, float]] = Field(default_factory=dict)
    heart_rate_mean: float | None
    respiratory_rate_mean: float | None
    heart_rate_record_count: int = 0
    heart_rate_record_mean: float | None = None
    heart_rate_ci95_half_width: float | None = None
    respiratory_rate_record_count: int = 0
    respiratory_rate_record_mean: float | None = None
    respiratory_rate_ci95_half_width: float | None = None
    respiratory_rate_night_record_count: int = 0
    respiratory_rate_night_record_mean: float | None = None
    respiratory_rate_day_record_count: int = 0
    respiratory_rate_day_record_mean: float | None = None
    # Sleep continuity, never clinical stages.
    sleep_longest_bout_minutes: float | None = None
    sleep_bout_count: int | None = None
    sleep_fragmentation_index: float | None = None
    # Outing counts are floors: sampling gaps can hide whole outings.
    outings_count: int | None = None
    outings_total_minutes: float | None = None
    outings: list[OutingDetail] = Field(default_factory=list)
    gps_distance_km: float

    @field_validator("hourly_minutes_by_category", mode="before")
    @classmethod
    def _coerce_hour_keys_to_int(cls, value: Any) -> Any:
        """JSONB round-trips dict keys as strings. Coerce back to int 0..23."""
        if not isinstance(value, dict):
            return value
        coerced: dict[int, dict[str, float]] = {}
        for key, row in value.items():
            try:
                hour = int(key)
            except (TypeError, ValueError):
                continue
            coerced[hour] = row
        return coerced


class TractiveRollupsResponse(BaseModel):
    """List wrapper so we can add cursor/pagination later without a breaking change."""

    daily: list[TractiveDailySummary] = Field(default_factory=list)


_MINUTES_PER_HOUR = 60.0


def _hours_rounded(minutes: float) -> float:
    """Convert a minute total to hours, rounded to 2dp."""
    return round(minutes / _MINUTES_PER_HOUR, 2)


def _hours_rounded_or_none(minutes: float | None) -> float | None:
    return None if minutes is None else _hours_rounded(minutes)


class MetricDayRow(BaseModel):
    """One day of a dog's metrics, already converted into the units we report.

    Durations arrive from the rollup in minutes and leave here in hours, and
    ``total_sleep_hours`` is summed here, so no caller and no language model ever
    does unit arithmetic. Field names are the contract the metric registry reads by.

    A value of None means the tracker recorded nothing for that metric that day,
    which is not the same as zero. The vitals are None on plenty of real days:
    readings taken while the dog was moving get dropped as contaminated.
    """

    date: date_type

    total_sleep_hours: float
    night_sleep_hours: float
    day_sleep_hours: float
    longest_sleep_bout_hours: float | None
    sleep_bout_count: int | None
    sleep_fragmentation_index: float | None

    active_hours: float
    moderate_hours: float
    low_intensity_hours: float
    no_signal_hours: float

    resting_heart_rate_bpm: float | None
    resting_heart_rate_reading_count: int
    resting_heart_rate_ci95_half_width: float | None
    resting_respiratory_rate_per_minute: float | None
    resting_respiratory_rate_reading_count: int
    resting_respiratory_rate_ci95_half_width: float | None
    night_resting_respiratory_rate_per_minute: float | None
    night_resting_respiratory_rate_reading_count: int
    day_resting_respiratory_rate_per_minute: float | None
    day_resting_respiratory_rate_reading_count: int

    outings_count: int | None
    outings_total_hours: float | None
    walking_distance_km: float


_METRIC_COLUMNS = (
    TractiveDayRollup.date,
    TractiveDayRollup.minutes_night_sleep,
    TractiveDayRollup.minutes_day_sleep,
    TractiveDayRollup.minutes_active,
    TractiveDayRollup.minutes_moderate,
    TractiveDayRollup.minutes_low_intensity,
    TractiveDayRollup.minutes_no_signal,
    TractiveDayRollup.sleep_longest_bout_minutes,
    TractiveDayRollup.sleep_bout_count,
    TractiveDayRollup.sleep_fragmentation_index,
    TractiveDayRollup.heart_rate_record_mean,
    TractiveDayRollup.heart_rate_record_count,
    TractiveDayRollup.heart_rate_ci95_half_width,
    TractiveDayRollup.respiratory_rate_record_mean,
    TractiveDayRollup.respiratory_rate_record_count,
    TractiveDayRollup.respiratory_rate_ci95_half_width,
    TractiveDayRollup.respiratory_rate_night_record_mean,
    TractiveDayRollup.respiratory_rate_night_record_count,
    TractiveDayRollup.respiratory_rate_day_record_mean,
    TractiveDayRollup.respiratory_rate_day_record_count,
    TractiveDayRollup.outings_count,
    TractiveDayRollup.outings_total_minutes,
    TractiveDayRollup.gps_distance_km,
)


def _to_metric_day_row(row: Any) -> MetricDayRow:
    """Map one selected rollup row into the reported units.

    The vitals read the record-level means rather than the sample-level ones: a
    measurement burst repeats near-identical values, so averaging samples overstates
    precision, and bursts contaminated by movement are dropped upstream.
    """
    return MetricDayRow(
        date=row.date,
        total_sleep_hours=_hours_rounded(row.minutes_night_sleep + row.minutes_day_sleep),
        night_sleep_hours=_hours_rounded(row.minutes_night_sleep),
        day_sleep_hours=_hours_rounded(row.minutes_day_sleep),
        longest_sleep_bout_hours=_hours_rounded_or_none(row.sleep_longest_bout_minutes),
        sleep_bout_count=row.sleep_bout_count,
        sleep_fragmentation_index=row.sleep_fragmentation_index,
        active_hours=_hours_rounded(row.minutes_active),
        moderate_hours=_hours_rounded(row.minutes_moderate),
        low_intensity_hours=_hours_rounded(row.minutes_low_intensity),
        no_signal_hours=_hours_rounded(row.minutes_no_signal),
        resting_heart_rate_bpm=row.heart_rate_record_mean,
        resting_heart_rate_reading_count=row.heart_rate_record_count,
        resting_heart_rate_ci95_half_width=row.heart_rate_ci95_half_width,
        resting_respiratory_rate_per_minute=row.respiratory_rate_record_mean,
        resting_respiratory_rate_reading_count=row.respiratory_rate_record_count,
        resting_respiratory_rate_ci95_half_width=row.respiratory_rate_ci95_half_width,
        night_resting_respiratory_rate_per_minute=row.respiratory_rate_night_record_mean,
        night_resting_respiratory_rate_reading_count=row.respiratory_rate_night_record_count,
        day_resting_respiratory_rate_per_minute=row.respiratory_rate_day_record_mean,
        day_resting_respiratory_rate_reading_count=row.respiratory_rate_day_record_count,
        outings_count=row.outings_count,
        outings_total_hours=_hours_rounded_or_none(row.outings_total_minutes),
        walking_distance_km=row.gps_distance_km,
    )


def window_start_date(days: int, today: date_type) -> date_type:
    return today - timedelta(days=max(1, days) - 1)


async def fetch_metric_window(
    session: AsyncSession,
    pet_id: uuid.UUID,
    days: int,
    today: date_type | None = None,
) -> list[MetricDayRow]:
    window_end = today if today is not None else date_type.today()
    statement = (
        select(*_METRIC_COLUMNS)
        .where(
            TractiveDayRollup.pet_id == pet_id,
            TractiveDayRollup.date >= window_start_date(days, window_end),
            TractiveDayRollup.date <= window_end,
        )
        .order_by(TractiveDayRollup.date.desc())
        .limit(days)
    )
    rows = list((await session.execute(statement)).all())
    rows.sort(key=lambda row: row.date)
    return [_to_metric_day_row(row) for row in rows]


async def fetch_latest_metric_date(session: AsyncSession, pet_id: uuid.UUID) -> date_type | None:
    statement = (
        select(TractiveDayRollup.date)
        .where(TractiveDayRollup.pet_id == pet_id)
        .order_by(TractiveDayRollup.date.desc())
        .limit(1)
    )
    return (await session.execute(statement)).scalar_one_or_none()


async def fetch_metric_on_date(
    session: AsyncSession, pet_id: uuid.UUID, day: date_type
) -> MetricDayRow | None:
    """Return ``pet_id``'s metrics for one calendar day, or None when it has no rollup."""
    statement = select(*_METRIC_COLUMNS).where(
        TractiveDayRollup.pet_id == pet_id, TractiveDayRollup.date == day
    )
    row = (await session.execute(statement)).first()
    return None if row is None else _to_metric_day_row(row)


class TractivePetDataReader:
    """Per-request, pet-scoped adapter that the agent's metric tools depend on.

    Binds the request session and the owner-verified pet, so a tool can choose only
    the metric and the time window, never whose data it reads. Built fresh per
    request, so no session is ever shared across concurrent requests.
    """

    def __init__(self, session: AsyncSession, pet_id: uuid.UUID) -> None:
        self._session = session
        self._pet_id = pet_id

    async def fetch_window(self, days: int) -> list[MetricDayRow]:
        return await fetch_metric_window(self._session, self._pet_id, days)

    async def fetch_on_date(self, day: date_type) -> MetricDayRow | None:
        return await fetch_metric_on_date(self._session, self._pet_id, day)

    async def fetch_latest_date(self) -> date_type | None:
        return await fetch_latest_metric_date(self._session, self._pet_id)


async def fetch_recent_rollups(
    session: AsyncSession, pet_id: uuid.UUID, days: int
) -> TractiveRollupsResponse:
    """Return the most recent ``days`` rollups for ``pet_id``, oldest-first."""
    statement = (
        select(TractiveDayRollup)
        .where(TractiveDayRollup.pet_id == pet_id)
        .order_by(TractiveDayRollup.date.desc())
        .limit(days)
    )
    result = await session.execute(statement)
    rows = list(result.scalars().all())
    rows.sort(key=lambda row: row.date)  # final response is ascending by date
    return TractiveRollupsResponse(
        daily=[
            TractiveDailySummary(
                date=row.date,
                minutes_active=row.minutes_active,
                minutes_low_intensity=row.minutes_low_intensity,
                minutes_moderate=row.minutes_moderate,
                minutes_night_sleep=row.minutes_night_sleep,
                minutes_day_sleep=row.minutes_day_sleep,
                minutes_no_signal=row.minutes_no_signal,
                # JSONB hands back str keys; the field_validator coerces to int.
                hourly_minutes_by_category=row.hourly_minutes_by_category,  # type: ignore[arg-type]
                heart_rate_mean=row.heart_rate_mean,
                respiratory_rate_mean=row.respiratory_rate_mean,
                heart_rate_record_count=row.heart_rate_record_count,
                heart_rate_record_mean=row.heart_rate_record_mean,
                heart_rate_ci95_half_width=row.heart_rate_ci95_half_width,
                respiratory_rate_record_count=row.respiratory_rate_record_count,
                respiratory_rate_record_mean=row.respiratory_rate_record_mean,
                respiratory_rate_ci95_half_width=row.respiratory_rate_ci95_half_width,
                respiratory_rate_night_record_count=row.respiratory_rate_night_record_count,
                respiratory_rate_night_record_mean=row.respiratory_rate_night_record_mean,
                respiratory_rate_day_record_count=row.respiratory_rate_day_record_count,
                respiratory_rate_day_record_mean=row.respiratory_rate_day_record_mean,
                sleep_longest_bout_minutes=row.sleep_longest_bout_minutes,
                sleep_bout_count=row.sleep_bout_count,
                sleep_fragmentation_index=row.sleep_fragmentation_index,
                outings_count=row.outings_count,
                outings_total_minutes=row.outings_total_minutes,
                # JSONB hands back dicts; pydantic parses them into OutingDetail.
                outings=row.outings,  # type: ignore[arg-type]
                gps_distance_km=row.gps_distance_km,
            )
            for row in rows
        ]
    )

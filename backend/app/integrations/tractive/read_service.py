"""Read-side queries against ``tractive_day_rollup`` for dashboard display."""

from __future__ import annotations

import uuid
from datetime import date as date_type
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tractive.models import TractiveDayRollup


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


class SleepSummary(BaseModel):
    """Averaged sleep over a recent window, computed server-side.

    Averages are taken over the days that actually have a rollup, and
    ``days_with_data`` is reported next to ``days_requested`` so a caller can
    caveat missing days instead of pretending the window was fully covered. All
    three averages are None exactly when there is no data in the window.
    """

    days_requested: int
    days_with_data: int
    average_total_sleep_hours: float | None
    average_night_sleep_hours: float | None
    average_day_sleep_hours: float | None
    start_date: date_type | None
    end_date: date_type | None


def _mean_hours_rounded(minutes: list[float]) -> float:
    """Average a list of per-day minute totals and return hours, rounded to 2dp."""
    return round(sum(minutes) / len(minutes) / _MINUTES_PER_HOUR, 2)


async def summarize_sleep(session: AsyncSession, pet_id: uuid.UUID, days: int) -> SleepSummary:
    """Average night, day, and total sleep over ``pet_id``'s most recent ``days`` rollups.

    The average is computed here, not by the caller, so a language model never has
    to do the arithmetic. Callers bound ``days`` to a sensible window before calling.
    """
    statement = (
        select(
            TractiveDayRollup.date,
            TractiveDayRollup.minutes_night_sleep,
            TractiveDayRollup.minutes_day_sleep,
        )
        .where(TractiveDayRollup.pet_id == pet_id)
        .order_by(TractiveDayRollup.date.desc())
        .limit(days)
    )
    rows = list((await session.execute(statement)).all())
    if not rows:
        return SleepSummary(
            days_requested=days,
            days_with_data=0,
            average_total_sleep_hours=None,
            average_night_sleep_hours=None,
            average_day_sleep_hours=None,
            start_date=None,
            end_date=None,
        )
    night_minutes = [row.minutes_night_sleep for row in rows]
    day_minutes = [row.minutes_day_sleep for row in rows]
    total_minutes = [night + day for night, day in zip(night_minutes, day_minutes, strict=True)]
    dates = [row.date for row in rows]
    return SleepSummary(
        days_requested=days,
        days_with_data=len(rows),
        average_total_sleep_hours=_mean_hours_rounded(total_minutes),
        average_night_sleep_hours=_mean_hours_rounded(night_minutes),
        average_day_sleep_hours=_mean_hours_rounded(day_minutes),
        start_date=min(dates),
        end_date=max(dates),
    )


class TractiveSleepReader:
    """Per-request, pet-scoped adapter that the agent's sleep tool depends on.

    Binds the request session and the owner-verified pet, so the tool can choose
    only the time window and never widen its scope to another owner's pet. Built
    fresh per request, so no session is ever shared across concurrent requests.
    """

    def __init__(self, session: AsyncSession, pet_id: uuid.UUID) -> None:
        self._session = session
        self._pet_id = pet_id

    async def summarize_sleep(self, days: int) -> SleepSummary:
        return await summarize_sleep(self._session, self._pet_id, days)


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
                gps_distance_km=row.gps_distance_km,
            )
            for row in rows
        ]
    )

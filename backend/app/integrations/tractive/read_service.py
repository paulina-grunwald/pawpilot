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

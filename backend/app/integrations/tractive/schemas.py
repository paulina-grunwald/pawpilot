"""Pydantic domain models for processed Tractive data.

These are the canonical in-memory shapes produced by the consolidation pipeline.
Both ingestion paths (GDPR-export upload, live-API fetch) populate `PerDayRollup`,
which is then persisted to `tractive_day_rollup`.

Raw upstream payloads (the JSON shapes Tractive returns) are intentionally not
modeled here — they're stored as opaque JSONB in `tractive_raw_payload` so we
can re-run the pipeline if the consolidation logic changes.
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TractiveSource(StrEnum):
    """Where the data originated."""

    GDPR_EXPORT = "gdpr_export"
    LIVE_API = "live_api"


class TractivePayloadType(StrEnum):
    """The five raw payload kinds Tractive's GDPR export contains.

    The live-API path produces the same logical groupings, even if endpoint
    names differ — we normalize to these labels for the audit table.
    """

    ACTIVITY_DATA = "activity_data"
    POSITION_REPORTS = "position_reports"
    HARDWARE_REPORTS = "hardware_reports"
    RESTING_HEART_RATES = "resting_heart_rates"
    RESTING_RESPIRATORY_RATES = "resting_respiratory_rates"


class ActivityMinutes(BaseModel):
    """Per-category daily minute totals, computed from `activityCategories`."""

    active: float = 0.0
    low_intensity: float = 0.0
    moderate: float = 0.0
    night_sleep: float = 0.0
    day_sleep: float = 0.0
    no_signal: float = 0.0


class VitalStats(BaseModel):
    """Aggregate stats for a vital sign across a single day."""

    n_samples: int = Field(ge=0)
    mean: float | None = None
    min: float | None = None
    max: float | None = None
    samples: list[float] = Field(default_factory=list)


class PositionSummary(BaseModel):
    """Daily summary of GPS / phone-fallback positions."""

    count: int = Field(ge=0)
    by_sensor: dict[str, int] = Field(default_factory=dict)
    first_time: datetime | None = None
    last_time: datetime | None = None
    distance_km: float = Field(ge=0.0)
    segments_counted: int = Field(ge=0)
    segments_dropped: int = Field(ge=0)


class TrackerSummary(BaseModel):
    """Hardware-side daily summary: battery, temperature, charging events."""

    battery_min: int | None = None
    battery_max: int | None = None
    temperature_min: float | None = None
    temperature_max: float | None = None
    n_charging_starts: int = Field(ge=0, default=0)


class PerDayRollup(BaseModel):
    """One day of processed Tractive data for one pet.

    The hourly distribution uses local-hour keys (0..23). Stored as
    `dict[int, ...]` here; JSONB will round-trip the keys as strings — the
    persistence layer is responsible for coercing on read.
    """

    date: date_type
    minutes: ActivityMinutes
    hourly_minutes_by_category: dict[int, dict[str, float]] = Field(default_factory=dict)
    resting_heart_rate: VitalStats
    resting_respiratory_rate: VitalStats
    positions: PositionSummary
    tracker: TrackerSummary

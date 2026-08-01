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


class VitalRecordStats(BaseModel):
    """Record-level aggregate for a vital sign across a single day.

    A record is one measurement event: a burst of samples taken together.
    Bursts repeat near-identical values, so sample-level aggregation overstates
    precision. Records whose burst contains any sample above the artifact
    ceiling are dropped as non-resting contamination before aggregating.
    """

    record_count: int = Field(ge=0, default=0)
    mean: float | None = None
    ci95_half_width: float | None = None


class RespiratoryNightDaySplit(BaseModel):
    """Record-level resting respiratory rate split by the night-sleep window.

    Night resting respiratory rate is the reading vets ask owners to watch,
    so it is aggregated separately from daytime records. Descriptive only.
    """

    night_record_count: int = Field(ge=0, default=0)
    night_mean: float | None = None
    day_record_count: int = Field(ge=0, default=0)
    day_mean: float | None = None


class SleepArchitecture(BaseModel):
    """Sleep continuity for one day, derived by walking the activity timeline.

    These describe how consolidated rest was, never clinical sleep stages:
    the tracker cannot see deep or light sleep and neither can we. Days with
    long no-signal stretches understate rest, so callers should caveat them.

    None on every field means the day had no activity timeline to walk, so
    continuity could not be derived at all. That is not the same as a derived
    zero, which means the timeline was read and no rest reached the bout minimum.
    """

    longest_bout_minutes: float | None = Field(default=None, ge=0.0)
    bout_count: int | None = Field(default=None, ge=0)
    fragmentation_index: float | None = Field(default=None, ge=0.0)


class OutingDetail(BaseModel):
    """One detected outing: a run of GPS fixes away from the derived home.

    Durations are measured first-to-last away fix, so the walk's leaving and
    returning legs inside the home radius are cut off. Callers should present
    the duration as a floor, never an exact figure.
    """

    started_at: datetime
    ended_at: datetime
    duration_minutes: float = Field(ge=0.0)
    max_distance_meters: float = Field(ge=0.0)
    fix_count: int = Field(ge=0)


class OutingSummary(BaseModel):
    """Daily outings summary. The count is a floor: sampling gaps and collar
    off time can hide whole outings, so zero detected does not mean the dog
    never left home. One caveat in the other direction: outings are detected
    per local day, so a walk spanning midnight counts once on each side.

    A None count means outings could not be derived for that day at all, for
    example because no home location could be established from the GPS. That is
    not the same as a derived zero, which means the dog stayed home.
    """

    count: int | None = Field(default=None, ge=0)
    total_minutes: float | None = Field(default=None, ge=0.0)
    entries: list[OutingDetail] = Field(default_factory=list)


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
    resting_heart_rate_records: VitalRecordStats = Field(default_factory=VitalRecordStats)
    resting_respiratory_rate_records: VitalRecordStats = Field(default_factory=VitalRecordStats)
    respiratory_night_day: RespiratoryNightDaySplit = Field(
        default_factory=RespiratoryNightDaySplit
    )
    positions: PositionSummary
    tracker: TrackerSummary
    sleep_architecture: SleepArchitecture = Field(default_factory=SleepArchitecture)
    outings: OutingSummary = Field(default_factory=OutingSummary)
    # Home derived from the data (densest fix cluster), because the configured
    # geofence can be stale; same value on every day of a batch.
    home_latitude: float | None = None
    home_longitude: float | None = None

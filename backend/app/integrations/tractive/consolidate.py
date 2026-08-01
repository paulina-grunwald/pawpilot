"""Consolidate Tractive raw payloads into per-day rollups.

Pure functions: in → in-memory payload dicts, out → ``list[PerDayRollup]``.

This is the canonical consolidation pipeline. Both ingestion paths (GDPR-export
upload and live-API fetch) feed the same shape in here and get the same shape
back, so the activity-category decoding, vitals aggregation, and GPS distance
filtering live in exactly one place.

Category mapping — empirically verified against the API's
``progress.achieved_minutes``:
  * ``-1`` sums match API "active minutes" within rounding → ``active``
  * ``None`` = collar off-body or out of sync (large blocks when charging)
    → ``no_signal``
  * ``6``  = long inactive stretch bundling extended rest; split into
    ``night_sleep`` / ``day_sleep`` by local hour-of-day (see below)
  * ``7``  = medium segments during midday → ``day_sleep``
  * ``0``, ``1`` = small scattered segments — provisionally ``low_intensity`` /
    ``moderate``; the Tractive UI doesn't expose these as separate buckets.
"""

from __future__ import annotations

import bisect
import json
import math
import statistics
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.integrations.tractive.schemas import (
    ActivityMinutes,
    OutingDetail,
    OutingSummary,
    PerDayRollup,
    PositionSummary,
    RespiratoryNightDaySplit,
    SleepArchitecture,
    TrackerSummary,
    VitalRecordStats,
    VitalStats,
)


class MalformedTractivePayloadError(ValueError):
    """Raised when raw Tractive payloads are syntactically valid JSON but
    structurally wrong — e.g. an activity day missing ``gmtTime`` or
    ``activityCategories``, or a record whose shape the pipeline can't read.

    HTTP routes translate this into a 400 so a bad export surfaces as a clean
    client error instead of an unhandled 500 with a stack trace.
    """


CATEGORY_LABEL: dict[int | None, str] = {
    -1: "active",
    0: "low_intensity",
    1: "moderate",
    # Category 6 is Tractive's "long inactive stretch" bucket. On real-world data
    # it routinely totals 12-18 h/day, which makes it obvious it's not literally
    # night sleep — it bundles all extended rest periods, overnight or not.
    # We split it by local hour-of-day: the slice inside NIGHT_SLEEP_HOURS is
    # counted as `night_sleep`, everything else as `day_sleep`.
    6: "night_sleep",
    # Category 7 totals ~30-130 min/day on real data — empirically that matches
    # an owner's "my dog napped a couple hours in the afternoon" gut check,
    # so we keep this as the day-naps bucket regardless of hour-of-day.
    7: "day_sleep",
    None: "no_signal",
}

# Hours considered "night sleep window" — matches what Tractive's app shows
# (8:00 PM → 10:00 AM = 14 hours). Both cat 6 and cat 7 sleep minutes get
# bucketed into night vs day by which hour they fall in, not by which raw
# category. This matches Tractive's UI definition where the dot color on the
# 24h timeline only depends on whether the sleep block is inside that window.
# TODO: make this per-pet user-configurable.
NIGHT_SLEEP_HOURS = frozenset({20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9})

# Resting vitals use a narrower window than the sleep-UI one above. NIGHT_SLEEP_HOURS
# spans 14 h to match Tractive's timeline colouring and takes in the 08:00 activity
# peak, so averaging "night resting" over it folds in post-walk readings.
NIGHT_RESTING_VITALS_HOURS = frozenset({22, 23, 0, 1, 2, 3, 4, 5})
SLEEP_RAW_CATEGORIES = frozenset({6, 7})

EARTH_RADIUS_KM = 6371.0
GPS_ACCURACY_METERS_MAX = 100
GPS_SPEED_KMH_MAX = 50

# Artifact ceilings for record-level vitals. A "resting" burst containing any
# sample above the ceiling is motion contamination (e.g. a 146 bpm reading
# taken mid-play), not a resting measurement, and is dropped whole. The heart
# rate ceiling is the top of the resting range the dashboard itself calls normal
# (VITAL_RANGES.restingHeartRateBpm): below that a reading may well be a small or
# young dog at rest, and discarding it drops every record such a dog produces.
HEART_RATE_ARTIFACT_CEILING_BPM = 130.0
RESPIRATORY_RATE_ARTIFACT_CEILING = 34.0

CI95_Z_SCORE = 1.96

# Outing detection. Home is derived from the data because the configured
# geofence can be stale (the real export's fence points at a previous
# address 3.5 km away). The grid precision of 3 decimal places is roughly a
# 110 m cell at mid latitudes.
HOME_CELL_DECIMAL_PLACES = 3
HOME_MINIMUM_FIXES = 10
# Home is re-derived per day over a centred window of surrounding days, so an
# export spanning a house move tracks the move instead of calling every fix at
# the new address an outing from the old one.
HOME_WINDOW_DAYS = 7
HOME_RADIUS_METERS = 100.0
OUTING_SPLIT_GAP_MINUTES = 15.0
OUTING_MINIMUM_MINUTES = 5.0
OUTING_MINIMUM_FIXES = 2

# Sleep-architecture bout detection over the per-minute rest timeline.
# A minute counts as rest when at least this fraction of its seconds are in
# a sleep category; brief arousals up to the gap tolerance stay inside one
# bout, and bouts shorter than the minimum are treated as fragmented rest
# rather than a consolidated sleep stretch.
SLEEP_MINUTE_REST_FRACTION = 0.75
SLEEP_BOUT_GAP_TOLERANCE_MINUTES = 5
SLEEP_BOUT_MINIMUM_MINUTES = 20
MINUTES_PER_DAY = 1440
MINUTES_PER_HOUR = 60
SECONDS_PER_MINUTE = 60


class GdprExportPayloads(BaseModel):
    """The five raw payload lists pulled from a Tractive GDPR export.

    Stays as ``list[dict]`` rather than fully modeled — the upstream contract
    is opaque to us and we store these blobs as JSONB for re-processing.
    """

    activity_data: list[dict[str, Any]]
    position_reports: list[dict[str, Any]]
    hardware_reports: list[dict[str, Any]]
    resting_heart_rates: list[dict[str, Any]]
    resting_respiratory_rates: list[dict[str, Any]]


GDPR_FILENAMES: dict[str, str] = {
    "activity_data": "activity_data.json",
    "position_reports": "position_reports.json",
    "hardware_reports": "hardware_reports.json",
    "resting_heart_rates": "resting_heart_rates.json",
    "resting_respiratory_rates": "resting_respiratory_rates.json",
}


def load_gdpr_export(data_dir: Path) -> GdprExportPayloads:
    """Read the five GDPR JSON files from disk into a typed envelope."""
    return GdprExportPayloads(
        **{
            field: json.loads((data_dir / filename).read_text())
            for field, filename in GDPR_FILENAMES.items()
        }
    )


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def haversine_km(latitude1: float, longitude1: float, latitude2: float, longitude2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    latitude1_rad = math.radians(latitude1)
    latitude2_rad = math.radians(latitude2)
    delta_latitude_rad = math.radians(latitude2 - latitude1)
    delta_longitude_rad = math.radians(longitude2 - longitude1)
    haversine_value = (
        math.sin(delta_latitude_rad / 2) ** 2
        + math.cos(latitude1_rad) * math.cos(latitude2_rad) * math.sin(delta_longitude_rad / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(haversine_value))


def compute_distance_km(positions: list[dict[str, Any]]) -> tuple[float, int, int]:
    """Sum great-circle distances between consecutive collar positions.

    Returns ``(km, segments_counted, segments_dropped)``.

    Filters: drop owner-phone fallbacks; drop segments implying >50 km/h
    (almost always a bad GPS fix — dogs don't run that fast); drop points
    with horizontal accuracy worse than 100 m.
    """
    points = _usable_position_fixes(positions)
    points.sort(key=lambda position: position["time"])

    total_km = 0.0
    segments_counted = 0
    segments_dropped = 0
    for start, end in pairwise(points):
        latitude1, longitude1 = start["latlong"]
        latitude2, longitude2 = end["latlong"]
        segment_km = haversine_km(latitude1, longitude1, latitude2, longitude2)
        delta_seconds = (parse_iso(end["time"]) - parse_iso(start["time"])).total_seconds()
        if delta_seconds <= 0:
            continue
        speed_kmh = segment_km / (delta_seconds / 3600)
        if speed_kmh > GPS_SPEED_KMH_MAX:
            segments_dropped += 1
            continue
        total_km += segment_km
        segments_counted += 1
    return round(total_km, 2), segments_counted, segments_dropped


def offset_selector_from_activity(
    activity_data: list[dict[str, Any]],
) -> Callable[[datetime], float]:
    """Build a function mapping a UTC moment → the GMT offset (in hours, may be
    fractional) in effect then, using the nearest activity day's ``gmtOffset``.

    Activity days carry a per-day ``gmtOffset``; position/hardware reports do
    not. Picking the temporally-nearest activity day's offset keeps each report
    on the correct local date across a DST change or a half-hour timezone
    (e.g. +05:30), instead of truncating to whole hours and applying a single
    global offset to the entire export.
    """
    day_offsets = sorted(
        (
            datetime.fromtimestamp(day["gmtTime"] / 1000, tz=UTC),
            float(day["gmtOffset"]) / 3_600_000,
        )
        for day in activity_data
    )
    instants = [instant for instant, _ in day_offsets]
    offsets = [offset for _, offset in day_offsets]

    def offset_for(moment: datetime) -> float:
        index = bisect.bisect_left(instants, moment)
        if index == 0:
            return offsets[0]
        if index == len(instants):
            return offsets[-1]
        before_gap = moment - instants[index - 1]
        after_gap = instants[index] - moment
        return offsets[index - 1] if before_gap <= after_gap else offsets[index]

    return offset_for


def index_by_local_date(
    items: list[dict[str, Any]],
    time_key: str,
    offset_selector: Callable[[datetime], float],
) -> dict[str, list[dict[str, Any]]]:
    """Group items by local date string, choosing each item's UTC offset via
    ``offset_selector`` (so DST/half-hour timezones bucket correctly).

    Each day's items are returned in chronological order so callers can rely on
    ``[0]``/``[-1]`` being the day's first/last event and on adjacent-pair scans
    (e.g. charge-cycle detection) being correct regardless of the order the raw
    export happened to list records in.
    """
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        moment = parse_iso(item[time_key])
        local_time = moment + timedelta(hours=offset_selector(moment))
        by_date[local_time.strftime("%Y-%m-%d")].append(item)
    for items_for_date in by_date.values():
        items_for_date.sort(key=lambda item: parse_iso(item[time_key]))
    return by_date


def decode_activity_day(
    day: dict[str, Any],
) -> tuple[str, ActivityMinutes, dict[int, dict[str, float]]]:
    """Return ``(local_date, ActivityMinutes, hourly_minutes_by_category)``."""
    gmt = datetime.fromtimestamp(day["gmtTime"] / 1000, tz=UTC)
    offset_hours = day["gmtOffset"] / 3_600_000
    local = gmt + timedelta(hours=offset_hours)
    date_str = local.strftime("%Y-%m-%d")

    total_seconds: dict[str, int] = defaultdict(int)
    hourly: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    # The activity run-length timeline starts at LOCAL midnight, not GMT midnight.
    # Verified against GPS fixes, whose UTC timestamps are independent of this
    # encoding: active minutes bucketed by cursor-hour correlate +0.95 with GPS
    # "away from home" by UTC hour under the local-start alignment, and -0.14 under
    # a GMT-start alignment (best alignment is local-start on 24/24 days). So the
    # cursor hour already IS the local hour — adding offset_hours here would shift
    # every bucket by the offset. offset_hours is still used above for date_str.
    cursor = 0  # seconds since start of the local day
    for seconds, category in day["activityCategories"]:
        base_label = CATEGORY_LABEL.get(category, f"unknown_{category}")
        remaining = seconds
        while remaining > 0:
            chunk = min(remaining, 3600 - (cursor % 3600))
            local_hour = int((cursor // 3600) % 24)
            # Both cat 6 and cat 7 are sleep categories. Tractive's app splits
            # them into "night sleep" vs "day sleep" by whether the block lies
            # inside the 20:00..09:59 window — NOT by raw category. We mirror
            # that so our numbers match what users see in their Tractive app.
            if category in SLEEP_RAW_CATEGORIES:
                chunk_label = "night_sleep" if local_hour in NIGHT_SLEEP_HOURS else "day_sleep"
            else:
                chunk_label = base_label
            total_seconds[chunk_label] += chunk
            hourly[local_hour][chunk_label] += chunk
            cursor += chunk
            remaining -= chunk

    minutes = ActivityMinutes(
        active=round(total_seconds.get("active", 0) / 60, 1),
        low_intensity=round(total_seconds.get("low_intensity", 0) / 60, 1),
        moderate=round(total_seconds.get("moderate", 0) / 60, 1),
        night_sleep=round(total_seconds.get("night_sleep", 0) / 60, 1),
        day_sleep=round(total_seconds.get("day_sleep", 0) / 60, 1),
        no_signal=round(total_seconds.get("no_signal", 0) / 60, 1),
    )
    hourly_minutes = {
        hour: {label: round(seconds / 60, 1) for label, seconds in row.items()}
        for hour, row in sorted(hourly.items())
    }
    return date_str, minutes, hourly_minutes


def _usable_position_fixes(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fixes trustworthy enough for geometry: collar-sourced, accurate, located."""
    usable = []
    for position in positions:
        if position.get("sensor_used") == "PHONE":
            continue
        accuracy = position.get("hori_accuracy")
        if accuracy is None or accuracy > GPS_ACCURACY_METERS_MAX:
            continue
        latlong = position.get("latlong")
        if not isinstance(latlong, list) or len(latlong) != 2:
            continue
        usable.append(position)
    return usable


def derive_home_center(position_reports: list[dict[str, Any]]) -> tuple[float, float] | None:
    """Home as the centroid of the densest ~110 m grid cell of usable fixes.

    Returns None when there are too few fixes to call any cell home, in which
    case outing detection is skipped rather than guessed.
    """
    fixes_by_cell: dict[tuple[float, float], list[tuple[float, float]]] = defaultdict(list)
    for position in _usable_position_fixes(position_reports):
        latitude, longitude = position["latlong"]
        cell = (
            round(latitude, HOME_CELL_DECIMAL_PLACES),
            round(longitude, HOME_CELL_DECIMAL_PLACES),
        )
        fixes_by_cell[cell].append((latitude, longitude))
    if not fixes_by_cell:
        return None
    densest = max(fixes_by_cell.values(), key=len)
    if len(densest) < HOME_MINIMUM_FIXES:
        return None
    return (
        sum(latitude for latitude, _ in densest) / len(densest),
        sum(longitude for _, longitude in densest) / len(densest),
    )


def home_center_by_local_date(
    positions_by_date: dict[str, list[dict[str, Any]]],
) -> dict[str, tuple[float, float] | None]:
    """Home per local date, derived from a centred window of nearby days."""
    dates = sorted(positions_by_date)
    ordinals = [date.fromisoformat(date_str).toordinal() for date_str in dates]
    centers: dict[str, tuple[float, float] | None] = {}
    for index, date_str in enumerate(dates):
        low = bisect.bisect_left(ordinals, ordinals[index] - HOME_WINDOW_DAYS)
        high = bisect.bisect_right(ordinals, ordinals[index] + HOME_WINDOW_DAYS)
        window = [
            position
            for neighbour in range(low, high)
            for position in positions_by_date[dates[neighbour]]
        ]
        centers[date_str] = derive_home_center(window)
    return centers


def detect_outings(
    positions: list[dict[str, Any]], home: tuple[float, float]
) -> list[OutingDetail]:
    """Outings for one local day: maximal runs of usable fixes beyond the home
    radius, split when an at-home fix intervenes or the run has a sampling gap
    of OUTING_SPLIT_GAP_MINUTES or more. Runs shorter than the minimums are
    discarded as jitter. Fixes are sorted by time here so callers cannot skew
    run detection with out-of-order input. A walk that truly spans local
    midnight is bucketed per day upstream and therefore counts as two shorter
    outings, one on each side of midnight.
    """
    ordered_fixes = sorted(_usable_position_fixes(positions), key=lambda fix: fix["time"])
    away_runs: list[list[tuple[datetime, float]]] = []
    current_run: list[tuple[datetime, float]] = []
    for position in ordered_fixes:
        latitude, longitude = position["latlong"]
        distance_meters = haversine_km(latitude, longitude, home[0], home[1]) * 1000
        moment = parse_iso(position["time"])
        if distance_meters <= HOME_RADIUS_METERS:
            if current_run:
                away_runs.append(current_run)
                current_run = []
            continue
        if current_run:
            gap_minutes = (moment - current_run[-1][0]).total_seconds() / 60
            if gap_minutes >= OUTING_SPLIT_GAP_MINUTES:
                away_runs.append(current_run)
                current_run = []
        current_run.append((moment, distance_meters))
    if current_run:
        away_runs.append(current_run)

    outings = []
    for run in away_runs:
        duration_minutes = (run[-1][0] - run[0][0]).total_seconds() / 60
        if len(run) < OUTING_MINIMUM_FIXES or duration_minutes < OUTING_MINIMUM_MINUTES:
            continue
        outings.append(
            OutingDetail(
                started_at=run[0][0],
                ended_at=run[-1][0],
                duration_minutes=round(duration_minutes, 1),
                max_distance_meters=round(max(distance for _, distance in run), 0),
                fix_count=len(run),
            )
        )
    return outings


def summarize_outings(outings: list[OutingDetail] | None) -> OutingSummary:
    if outings is None:
        return OutingSummary()
    return OutingSummary(
        count=len(outings),
        total_minutes=round(sum(outing.duration_minutes for outing in outings), 1),
        entries=outings,
    )


def _minute_states(activity_categories: list[list[Any]]) -> list[str]:
    """Collapse the RLE second timeline into per-minute rest/awake/no_signal
    states, majority-classified per minute.
    """
    rest_seconds = [0] * MINUTES_PER_DAY
    no_signal_seconds = [0] * MINUTES_PER_DAY
    cursor = 0
    for seconds, category in activity_categories:
        remaining = int(seconds)
        while remaining > 0 and cursor < MINUTES_PER_DAY * SECONDS_PER_MINUTE:
            minute_index = cursor // SECONDS_PER_MINUTE
            chunk = min(remaining, SECONDS_PER_MINUTE - (cursor % SECONDS_PER_MINUTE))
            if category in SLEEP_RAW_CATEGORIES:
                rest_seconds[minute_index] += chunk
            elif category is None:
                no_signal_seconds[minute_index] += chunk
            cursor += chunk
            remaining -= chunk
    states = []
    for minute_index in range(MINUTES_PER_DAY):
        if no_signal_seconds[minute_index] > SECONDS_PER_MINUTE / 2:
            states.append("no_signal")
        elif rest_seconds[minute_index] >= SECONDS_PER_MINUTE * SLEEP_MINUTE_REST_FRACTION:
            states.append("rest")
        else:
            states.append("awake")
    return states


def _rest_bouts(states: list[str]) -> list[tuple[int, int]]:
    """Maximal rest bouts as (start, end_exclusive) minute spans, tolerating
    awake gaps up to the tolerance and keeping only bouts at the minimum
    length. No-signal minutes end a bout: unclassified time is never scored
    as sleep.
    """
    bouts = []
    start: int | None = None
    awake_gap = 0
    for minute_index, state in enumerate(states):
        if state == "rest":
            if start is None:
                start = minute_index
            awake_gap = 0
        elif state == "awake" and start is not None:
            awake_gap += 1
            if awake_gap > SLEEP_BOUT_GAP_TOLERANCE_MINUTES:
                bouts.append((start, minute_index - awake_gap + 1))
                start = None
                awake_gap = 0
        elif state == "no_signal" and start is not None:
            bouts.append((start, minute_index - awake_gap))
            start = None
            awake_gap = 0
    if start is not None:
        bouts.append((start, len(states) - awake_gap))
    return [
        (bout_start, bout_end)
        for bout_start, bout_end in bouts
        if bout_end - bout_start >= SLEEP_BOUT_MINIMUM_MINUTES
    ]


def _consecutive_date_runs(sorted_dates: list[str]) -> list[list[str]]:
    runs: list[list[str]] = []
    for date_str in sorted_dates:
        current = date.fromisoformat(date_str)
        if runs and date.fromisoformat(runs[-1][-1]) + timedelta(days=1) == current:
            runs[-1].append(date_str)
        else:
            runs.append([date_str])
    return runs


def _bout_day_index(bout_start: int, bout_end: int) -> int:
    minutes_by_day: dict[int, int] = defaultdict(int)
    for minute_index in range(bout_start, bout_end):
        minutes_by_day[minute_index // MINUTES_PER_DAY] += 1
    return max(sorted(minutes_by_day), key=lambda day_index: minutes_by_day[day_index])


def _architecture_from_bouts(bouts: list[tuple[int, int]], states: list[str]) -> SleepArchitecture:
    if not bouts:
        return SleepArchitecture(longest_bout_minutes=0.0, bout_count=0)
    interruption_minutes = 0
    bout_rest_minutes = 0
    for bout_start, bout_end in bouts:
        for minute_index in range(bout_start, bout_end):
            if states[minute_index] == "awake":
                interruption_minutes += 1
            elif states[minute_index] == "rest":
                bout_rest_minutes += 1
    bout_rest_hours = bout_rest_minutes / MINUTES_PER_HOUR
    return SleepArchitecture(
        longest_bout_minutes=float(max(end - start for start, end in bouts)),
        bout_count=len(bouts),
        fragmentation_index=(
            round(interruption_minutes / bout_rest_hours, 1) if bout_rest_hours > 0 else None
        ),
    )


def sleep_architecture_by_local_date(
    activity_data: list[dict[str, Any]],
) -> dict[str, SleepArchitecture]:
    states_by_date: dict[str, list[str]] = {}
    for day in activity_data:
        date_str, _minutes, _hourly = decode_activity_day(day)
        states_by_date[date_str] = _minute_states(day["activityCategories"])

    architecture_by_date: dict[str, SleepArchitecture] = {}
    for run_dates in _consecutive_date_runs(sorted(states_by_date)):
        states: list[str] = []
        for date_str in run_dates:
            states.extend(states_by_date[date_str])
        bouts_by_day: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for bout_start, bout_end in _rest_bouts(states):
            bouts_by_day[_bout_day_index(bout_start, bout_end)].append((bout_start, bout_end))
        for day_index, date_str in enumerate(run_dates):
            architecture_by_date[date_str] = _architecture_from_bouts(
                bouts_by_day[day_index], states
            )
    return architecture_by_date


def sleep_architecture_from_activity(
    activity_categories: list[list[Any]],
) -> SleepArchitecture:
    if not activity_categories:
        return SleepArchitecture()
    states = _minute_states(activity_categories)
    return _architecture_from_bouts(_rest_bouts(states), states)


def stats_from_samples(samples: list[float]) -> VitalStats:
    if not samples:
        return VitalStats(n_samples=0, mean=None, min=None, max=None, samples=[])
    return VitalStats(
        n_samples=len(samples),
        mean=round(sum(samples) / len(samples), 1),
        min=min(samples),
        max=max(samples),
        samples=samples,
    )


def _record_means(records: list[dict[str, Any]], artifact_ceiling: float) -> list[float]:
    """One mean per accepted record; records with any sample above the ceiling
    (or with no samples) are dropped whole.
    """
    means: list[float] = []
    for record in records:
        samples = [float(sample) for sample in record.get("samples", [])]
        if not samples or max(samples) > artifact_ceiling:
            continue
        means.append(sum(samples) / len(samples))
    return means


def _ci95_half_width(record_means: list[float]) -> float | None:
    if len(record_means) < 2:
        return None
    standard_error = statistics.stdev(record_means) / math.sqrt(len(record_means))
    return round(CI95_Z_SCORE * standard_error, 2)


def record_stats_from_records(
    records: list[dict[str, Any]], artifact_ceiling: float
) -> VitalRecordStats:
    """Record-level daily stats: each measurement event counts once, however
    many samples its burst repeated, and contaminated bursts are rejected.
    """
    record_means = _record_means(records, artifact_ceiling)
    if not record_means:
        return VitalRecordStats()
    return VitalRecordStats(
        record_count=len(record_means),
        mean=round(statistics.mean(record_means), 1),
        ci95_half_width=_ci95_half_width(record_means),
    )


def _record_local_hour(record: dict[str, Any]) -> int | None:
    """Hour of day from a record's local_time, e.g. "12:23:31+03:00".

    Some records carry "HH:MM" without seconds, so the hour is whatever comes
    before the first colon rather than a fixed two-character slice.
    """
    local_time = record.get("local_time")
    if not isinstance(local_time, str) or not local_time:
        return None
    try:
        hour = int(local_time.split(":", 1)[0])
    except ValueError:
        return None
    return hour if 0 <= hour <= 23 else None


def respiratory_night_day_split(records: list[dict[str, Any]]) -> RespiratoryNightDaySplit:
    """Record-level resting respiratory rate split into the night-sleep window
    vs daytime, with the same artifact rejection as the daily record stats.
    """
    night_records: list[dict[str, Any]] = []
    day_records: list[dict[str, Any]] = []
    for record in records:
        hour = _record_local_hour(record)
        if hour is None:
            continue
        (night_records if hour in NIGHT_RESTING_VITALS_HOURS else day_records).append(record)
    night_means = _record_means(night_records, RESPIRATORY_RATE_ARTIFACT_CEILING)
    day_means = _record_means(day_records, RESPIRATORY_RATE_ARTIFACT_CEILING)
    return RespiratoryNightDaySplit(
        night_record_count=len(night_means),
        night_mean=round(statistics.mean(night_means), 1) if night_means else None,
        day_record_count=len(day_means),
        day_mean=round(statistics.mean(day_means), 1) if day_means else None,
    )


def build_per_day(payloads: GdprExportPayloads) -> list[PerDayRollup]:
    """Compute per-day rollups from a full set of raw payloads.

    Empty ``activity_data`` produces an empty result — there's nothing to
    anchor days against. Other payloads can be empty without breaking the
    pipeline; their per-day summaries simply come back zero/None.

    Structurally invalid payloads (valid JSON, wrong shape) raise
    ``MalformedTractivePayloadError`` so HTTP callers can return a 400 rather
    than leaking an unhandled 500.
    """
    if not payloads.activity_data:
        return []
    try:
        return _consolidate_payloads(payloads)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError, ValidationError) as error:
        raise MalformedTractivePayloadError(
            f"Tractive payload is structurally invalid: {error}"
        ) from error


def _consolidate_payloads(payloads: GdprExportPayloads) -> list[PerDayRollup]:
    """Core consolidation; assumes ``payloads.activity_data`` is non-empty.

    Raises ``KeyError``/``TypeError``/``ValueError``/``ValidationError`` on
    malformed input — ``build_per_day`` wraps those into
    ``MalformedTractivePayloadError``.
    """
    offset_selector = offset_selector_from_activity(payloads.activity_data)
    architecture_by_date = sleep_architecture_by_local_date(payloads.activity_data)
    positions_by_date = index_by_local_date(payloads.position_reports, "time", offset_selector)
    home_by_date = home_center_by_local_date(positions_by_date)
    hardware_by_date = index_by_local_date(payloads.hardware_reports, "time", offset_selector)
    heart_rates_by_date = {
        entry["local_date"]: entry["records"] for entry in payloads.resting_heart_rates
    }
    respiratory_rates_by_date = {
        entry["local_date"]: entry["records"] for entry in payloads.resting_respiratory_rates
    }

    rollups: list[PerDayRollup] = []
    for day in payloads.activity_data:
        date_str, minutes, hourly = decode_activity_day(day)

        heart_rate_records = heart_rates_by_date.get(date_str, [])
        respiratory_rate_records = respiratory_rates_by_date.get(date_str, [])
        heart_rate_samples = [
            sample for record in heart_rate_records for sample in record["samples"]
        ]
        respiratory_rate_samples = [
            sample for record in respiratory_rate_records for sample in record["samples"]
        ]
        positions_today = positions_by_date.get(date_str, [])
        home_center = home_by_date.get(date_str)
        hardware_today = hardware_by_date.get(date_str, [])

        battery = [
            entry["battery_level"]
            for entry in hardware_today
            if entry.get("battery_level") is not None
        ]
        temperatures = [
            entry["temperature"] for entry in hardware_today if entry.get("temperature") is not None
        ]
        charging_starts = sum(
            1
            for index in range(1, len(hardware_today))
            if hardware_today[index].get("charger_connected")
            and not hardware_today[index - 1].get("charger_connected")
        )

        sensor_counts: dict[str, int] = defaultdict(int)
        for position in positions_today:
            sensor_counts[position.get("sensor_used", "unknown")] += 1
        distance_km, segments_counted, segments_dropped = compute_distance_km(positions_today)

        rollups.append(
            PerDayRollup(
                date=datetime.strptime(date_str, "%Y-%m-%d").date(),
                minutes=minutes,
                hourly_minutes_by_category=hourly,
                resting_heart_rate=stats_from_samples(heart_rate_samples),
                resting_respiratory_rate=stats_from_samples(respiratory_rate_samples),
                resting_heart_rate_records=record_stats_from_records(
                    heart_rate_records, HEART_RATE_ARTIFACT_CEILING_BPM
                ),
                resting_respiratory_rate_records=record_stats_from_records(
                    respiratory_rate_records, RESPIRATORY_RATE_ARTIFACT_CEILING
                ),
                respiratory_night_day=respiratory_night_day_split(respiratory_rate_records),
                positions=PositionSummary(
                    count=len(positions_today),
                    by_sensor=dict(sensor_counts),
                    first_time=parse_iso(positions_today[0]["time"]) if positions_today else None,
                    last_time=parse_iso(positions_today[-1]["time"]) if positions_today else None,
                    distance_km=distance_km,
                    segments_counted=segments_counted,
                    segments_dropped=segments_dropped,
                ),
                tracker=TrackerSummary(
                    battery_min=min(battery) if battery else None,
                    battery_max=max(battery) if battery else None,
                    temperature_min=min(temperatures) if temperatures else None,
                    temperature_max=max(temperatures) if temperatures else None,
                    n_charging_starts=charging_starts,
                ),
                sleep_architecture=architecture_by_date.get(date_str, SleepArchitecture()),
                outings=summarize_outings(
                    detect_outings(positions_today, home_center) if home_center else None
                ),
                home_latitude=home_center[0] if home_center else None,
                home_longitude=home_center[1] if home_center else None,
            )
        )

    rollups.sort(key=lambda rollup: rollup.date)
    return rollups

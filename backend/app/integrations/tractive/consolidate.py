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
  * ``6``  = long contiguous block at start of GMT day (= 03:00 local)
    → ``night_sleep``
  * ``7``  = medium segments during midday → ``day_sleep``
  * ``0``, ``1`` = small scattered segments — provisionally ``low_intensity`` /
    ``moderate``; the Tractive UI doesn't expose these as separate buckets.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from app.integrations.tractive.schemas import (
    ActivityMinutes,
    PerDayRollup,
    PositionSummary,
    TrackerSummary,
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
    # We now split it by local hour-of-day: only the slice that falls in
    # NIGHT_SLEEP_HOURS gets counted as `night_sleep`. Daytime cat-6 minutes are
    # dropped from the named buckets (raw timeline is still in
    # tractive_raw_payload.payload if we want them back).
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
SLEEP_RAW_CATEGORIES = frozenset({6, 7})

EARTH_RADIUS_KM = 6371.0
GPS_ACCURACY_METERS_MAX = 100
GPS_SPEED_KMH_MAX = 50


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
    points = [
        position
        for position in positions
        if position.get("sensor_used") != "PHONE"
        and position.get("latlong")
        and (position.get("hori_accuracy") or 999) <= GPS_ACCURACY_METERS_MAX
    ]
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


def index_by_local_date(
    items: list[dict[str, Any]], time_key: str, offset_hours: int
) -> dict[str, list[dict[str, Any]]]:
    """Group items by local date string, using ``offset_hours`` from UTC.

    Each day's items are returned in chronological order so callers can rely on
    ``[0]``/``[-1]`` being the day's first/last event and on adjacent-pair scans
    (e.g. charge-cycle detection) being correct regardless of the order the raw
    export happened to list records in.
    """
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        local_time = parse_iso(item[time_key]) + timedelta(hours=offset_hours)
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

    cursor = 0  # seconds since start of GMT day
    for seconds, category in day["activityCategories"]:
        base_label = CATEGORY_LABEL.get(category, f"unknown_{category}")
        remaining = seconds
        while remaining > 0:
            chunk = min(remaining, 3600 - (cursor % 3600))
            local_hour = int(((cursor // 3600) + offset_hours) % 24)
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
    offset_hours = int(payloads.activity_data[0]["gmtOffset"] / 3_600_000)
    positions_by_date = index_by_local_date(payloads.position_reports, "time", offset_hours)
    hardware_by_date = index_by_local_date(payloads.hardware_reports, "time", offset_hours)
    heart_rates_by_date = {
        entry["local_date"]: entry["records"] for entry in payloads.resting_heart_rates
    }
    respiratory_rates_by_date = {
        entry["local_date"]: entry["records"] for entry in payloads.resting_respiratory_rates
    }

    rollups: list[PerDayRollup] = []
    for day in payloads.activity_data:
        date_str, minutes, hourly = decode_activity_day(day)

        heart_rate_samples = [
            sample
            for record in heart_rates_by_date.get(date_str, [])
            for sample in record["samples"]
        ]
        respiratory_rate_samples = [
            sample
            for record in respiratory_rates_by_date.get(date_str, [])
            for sample in record["samples"]
        ]
        positions_today = positions_by_date.get(date_str, [])
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
            )
        )

    rollups.sort(key=lambda rollup: rollup.date)
    return rollups

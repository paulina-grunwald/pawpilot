"""Unit tests for the Tractive consolidation pipeline."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.integrations.tractive.consolidate import (
    GdprExportPayloads,
    build_per_day,
    compute_distance_km,
    decode_activity_day,
    haversine_km,
    load_gdpr_export,
    stats_from_samples,
)


def test_haversine_zero_distance_for_same_point() -> None:
    assert haversine_km(44.4268, 26.1025, 44.4268, 26.1025) == 0.0


def test_haversine_known_distance_between_bucharest_and_sofia() -> None:
    # Bucharest center → Sofia center ≈ 296 km (known great-circle distance).
    distance = haversine_km(44.4268, 26.1025, 42.6977, 23.3219)
    assert 290 < distance < 305


def test_compute_distance_drops_phone_points() -> None:
    positions = [
        {
            "time": "2024-05-15T08:00:00Z",
            "latlong": [44.4268, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "PHONE",
        },
        {
            "time": "2024-05-15T08:30:00Z",
            "latlong": [44.4358, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "PHONE",
        },
    ]
    distance_km, segments_counted, segments_dropped = compute_distance_km(positions)
    assert distance_km == 0.0
    assert segments_counted == 0
    assert segments_dropped == 0


def test_compute_distance_drops_low_accuracy_points() -> None:
    positions = [
        {
            "time": "2024-05-15T08:00:00Z",
            "latlong": [44.4268, 26.1025],
            "hori_accuracy": 500,
            "sensor_used": "GPS",
        },
        {
            "time": "2024-05-15T08:30:00Z",
            "latlong": [44.4358, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
    ]
    distance_km, segments_counted, _ = compute_distance_km(positions)
    assert distance_km == 0.0
    assert segments_counted == 0


def test_compute_distance_drops_segments_implying_unrealistic_speed() -> None:
    # 1 km in 10 seconds → 360 km/h → must be dropped.
    positions = [
        {
            "time": "2024-05-15T08:00:00Z",
            "latlong": [44.4268, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
        {
            "time": "2024-05-15T08:00:10Z",
            "latlong": [44.4358, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
    ]
    distance_km, segments_counted, segments_dropped = compute_distance_km(positions)
    assert distance_km == 0.0
    assert segments_counted == 0
    assert segments_dropped == 1


def test_compute_distance_skips_pairs_with_non_positive_time_delta() -> None:
    positions = [
        {
            "time": "2024-05-15T08:00:00Z",
            "latlong": [44.4268, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
        {
            "time": "2024-05-15T08:00:00Z",
            "latlong": [44.4268, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
    ]
    distance_km, segments_counted, segments_dropped = compute_distance_km(positions)
    assert distance_km == 0.0
    assert segments_counted == 0
    assert segments_dropped == 0


def test_decode_activity_day_buckets_minutes_per_local_hour() -> None:
    day = {
        "gmtTime": 1_715_731_200_000,  # 2024-05-15 00:00 UTC → 03:00 local at +03
        "gmtOffset": 3 * 3_600_000,
        "activityCategories": [[3600, 6], [1800, -1], [1800, None]],
    }
    date_str, minutes, hourly = decode_activity_day(day)
    assert date_str == "2024-05-15"
    assert minutes.night_sleep == 60.0
    assert minutes.active == 30.0
    assert minutes.no_signal == 30.0
    # 1h sleep starts at local hour 3, 30m active + 30m no_signal land in hour 4
    assert hourly[3]["night_sleep"] == 60.0
    assert hourly[4]["active"] == 30.0
    assert hourly[4]["no_signal"] == 30.0


def test_decode_activity_day_splits_sleep_by_local_hour_window() -> None:
    # 10h of activity starting at local hour 3 lands the cursor at local hour 13
    # by the time cat 6 begins. Tractive's "night sleep" window is 20:00-09:59,
    # so cat 6 at hours 13 + 14 falls in the DAY window → counted as day_sleep.
    # The cat 7 chunk at hour 15 also falls in the day window → day_sleep.
    day = {
        "gmtTime": 1_715_731_200_000,
        "gmtOffset": 3 * 3_600_000,
        "activityCategories": [[36000, -1], [3600, 6], [3600, 6], [3600, 7]],
    }
    _, minutes, hourly = decode_activity_day(day)
    assert minutes.active == 600.0
    assert minutes.night_sleep == 0.0
    # 2 chunks of cat 6 + 1 chunk of cat 7, each 1h, all in day window.
    assert minutes.day_sleep == 180.0
    assert hourly[13]["day_sleep"] == 60.0
    assert hourly[14]["day_sleep"] == 60.0
    assert hourly[15]["day_sleep"] == 60.0


def test_decode_activity_day_counts_late_evening_cat_seven_as_night_sleep() -> None:
    # Cat 7 chunk that lands in the 20:00-09:59 window now counts as night_sleep
    # (Tractive's logic: sleep is sleep, the dot color depends on hour-of-day).
    # Set up cursor so cat 7 lands at local hour 21.
    day = {
        "gmtTime": 1_715_731_200_000,
        "gmtOffset": 3 * 3_600_000,
        # 18h of active fills hours 3..20, then 1h cat 7 at hour 21.
        "activityCategories": [[18 * 3600, -1], [3600, 7]],
    }
    _, minutes, _ = decode_activity_day(day)
    assert minutes.night_sleep == 60.0
    assert minutes.day_sleep == 0.0


def test_decode_activity_day_labels_unknown_categories() -> None:
    day = {
        "gmtTime": 1_715_731_200_000,
        "gmtOffset": 3 * 3_600_000,
        "activityCategories": [[3600, 99]],
    }
    _, minutes, _ = decode_activity_day(day)
    # 99 is not in the category map → falls into the unknown bucket and is
    # NOT counted in any of the named ActivityMinutes fields.
    assert minutes.active == 0
    assert minutes.night_sleep == 0


def test_stats_from_samples_empty_returns_nulls() -> None:
    stats = stats_from_samples([])
    assert stats.n_samples == 0
    assert stats.mean is None
    assert stats.min is None
    assert stats.max is None
    assert stats.samples == []


def test_stats_from_samples_computes_mean_min_max() -> None:
    stats = stats_from_samples([10.0, 20.0, 30.0])
    assert stats.n_samples == 3
    assert stats.mean == 20.0
    assert stats.min == 10.0
    assert stats.max == 30.0


def test_build_per_day_empty_activity_returns_empty_list() -> None:
    payloads = GdprExportPayloads(
        activity_data=[],
        position_reports=[],
        hardware_reports=[],
        resting_heart_rates=[],
        resting_respiratory_rates=[],
    )
    assert build_per_day(payloads) == []


def test_build_per_day_produces_one_rollup_per_activity_day(
    sample_gdpr_payloads: GdprExportPayloads,
) -> None:
    rollups = build_per_day(sample_gdpr_payloads)

    assert [rollup.date for rollup in rollups] == [date(2024, 5, 15), date(2024, 5, 16)]

    day_one = rollups[0]
    assert day_one.minutes.night_sleep == 60.0
    assert day_one.minutes.active == 30.0
    assert day_one.minutes.no_signal == 30.0
    assert day_one.resting_heart_rate.n_samples == 3
    assert day_one.resting_heart_rate.mean == 62.0
    assert day_one.resting_respiratory_rate.n_samples == 2
    assert day_one.resting_respiratory_rate.mean == 17.0
    # 3 raw position rows (2 GPS + 1 PHONE), but only 1 valid GPS segment counted.
    assert day_one.positions.count == 3
    assert day_one.positions.by_sensor == {"GPS": 2, "PHONE": 1}
    assert day_one.positions.segments_counted == 1
    assert day_one.positions.distance_km == pytest.approx(1.0, abs=0.05)
    assert day_one.tracker.battery_min == 60
    assert day_one.tracker.battery_max == 80
    assert day_one.tracker.temperature_min == 21.0
    assert day_one.tracker.temperature_max == 22.5
    assert day_one.tracker.n_charging_starts == 1

    day_two = rollups[1]
    # The 1h cat-7 chunk lands at local hour 3 (inside the 20:00-09:59 night
    # window), so the new logic buckets it as night_sleep, not day_sleep.
    assert day_two.minutes.night_sleep == 60.0
    assert day_two.minutes.day_sleep == 0.0
    # Day two has no positions or vitals — assert the zero/empty defaults.
    assert day_two.positions.count == 0
    assert day_two.positions.distance_km == 0.0
    assert day_two.resting_heart_rate.n_samples == 0
    assert day_two.tracker.battery_min is None


def test_load_gdpr_export_reads_five_json_files(
    tmp_path: Path, sample_gdpr_payloads: GdprExportPayloads
) -> None:
    (tmp_path / "activity_data.json").write_text(json.dumps(sample_gdpr_payloads.activity_data))
    (tmp_path / "position_reports.json").write_text(
        json.dumps(sample_gdpr_payloads.position_reports)
    )
    (tmp_path / "hardware_reports.json").write_text(
        json.dumps(sample_gdpr_payloads.hardware_reports)
    )
    (tmp_path / "resting_heart_rates.json").write_text(
        json.dumps(sample_gdpr_payloads.resting_heart_rates)
    )
    (tmp_path / "resting_respiratory_rates.json").write_text(
        json.dumps(sample_gdpr_payloads.resting_respiratory_rates)
    )
    loaded = load_gdpr_export(tmp_path)
    assert loaded.activity_data == sample_gdpr_payloads.activity_data
    assert len(loaded.position_reports) == 3
    assert len(loaded.hardware_reports) == 2

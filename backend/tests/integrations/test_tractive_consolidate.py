"""Unit tests for the Tractive consolidation pipeline."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from app.integrations.tractive.consolidate import (
    HEART_RATE_ARTIFACT_CEILING_BPM,
    RESPIRATORY_RATE_ARTIFACT_CEILING,
    GdprExportPayloads,
    MalformedTractivePayloadError,
    build_per_day,
    compute_distance_km,
    decode_activity_day,
    derive_home_center,
    detect_outings,
    haversine_km,
    home_center_by_local_date,
    load_gdpr_export,
    parse_iso,
    record_stats_from_records,
    respiratory_night_day_split,
    sleep_architecture_by_local_date,
    sleep_architecture_from_activity,
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
        "gmtTime": 1_715_731_200_000,  # 2024-05-15 00:00 UTC, +03 → local date 2024-05-15
        "gmtOffset": 3 * 3_600_000,
        "activityCategories": [[3600, 6], [1800, -1], [1800, None]],
    }
    date_str, minutes, hourly = decode_activity_day(day)
    assert date_str == "2024-05-15"
    assert minutes.night_sleep == 60.0
    assert minutes.active == 30.0
    assert minutes.no_signal == 30.0
    # The RLE starts at local midnight: 1h sleep in hour 0, then 30m active +
    # 30m no_signal in hour 1.
    assert hourly[0]["night_sleep"] == 60.0
    assert hourly[1]["active"] == 30.0
    assert hourly[1]["no_signal"] == 30.0


def test_decode_activity_day_splits_sleep_by_local_hour_window() -> None:
    # 10h of activity fills local hours 0..9, so cat 6 begins at local hour 10.
    # Tractive's "night sleep" window is 20:00-09:59, so cat 6 at hours 10 + 11
    # falls in the DAY window → counted as day_sleep. The cat 7 chunk at hour 12
    # also falls in the day window → day_sleep.
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
    assert hourly[10]["day_sleep"] == 60.0
    assert hourly[11]["day_sleep"] == 60.0
    assert hourly[12]["day_sleep"] == 60.0


def test_decode_activity_day_counts_late_evening_cat_seven_as_night_sleep() -> None:
    # Cat 7 chunk that lands in the 20:00-09:59 window now counts as night_sleep
    # (Tractive's logic: sleep is sleep, the dot color depends on hour-of-day).
    # Set up cursor so cat 7 lands at local hour 21.
    day = {
        "gmtTime": 1_715_731_200_000,
        "gmtOffset": 3 * 3_600_000,
        # 21h of active fills local hours 0..20, then 1h cat 7 at hour 21.
        "activityCategories": [[21 * 3600, -1], [3600, 7]],
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


def test_record_stats_empty_records_return_defaults() -> None:
    stats = record_stats_from_records([], HEART_RATE_ARTIFACT_CEILING_BPM)
    assert stats.record_count == 0
    assert stats.mean is None
    assert stats.ci95_half_width is None


def test_record_stats_single_burst_counts_once() -> None:
    # A burst of three near-identical samples is one measurement event, not
    # three independent readings.
    stats = record_stats_from_records(
        [{"samples": [70.0, 70.0, 70.0]}], HEART_RATE_ARTIFACT_CEILING_BPM
    )
    assert stats.record_count == 1
    assert stats.mean == 70.0
    assert stats.ci95_half_width is None


def test_record_stats_drops_contaminated_bursts_whole() -> None:
    stats = record_stats_from_records(
        [{"samples": [60.0, 146.0]}, {"samples": [64.0]}],
        HEART_RATE_ARTIFACT_CEILING_BPM,
    )
    assert stats.record_count == 1
    assert stats.mean == 64.0


def test_heart_rate_ceiling_keeps_a_small_dog_at_rest() -> None:
    """A 110-120 bpm resting burst is normal for a small dog, not motion artifact.

    VITAL_RANGES calls 50-130 normal, so a ceiling inside that band silently
    discards every record such a dog produces.
    """
    stats = record_stats_from_records(
        [{"samples": [112.0, 118.0]}], HEART_RATE_ARTIFACT_CEILING_BPM
    )
    assert stats.record_count == 1
    assert stats.mean == 115.0


def test_record_stats_keeps_bursts_at_exactly_the_ceiling() -> None:
    stats = record_stats_from_records(
        [{"samples": [HEART_RATE_ARTIFACT_CEILING_BPM]}], HEART_RATE_ARTIFACT_CEILING_BPM
    )
    assert stats.record_count == 1
    assert stats.mean == HEART_RATE_ARTIFACT_CEILING_BPM


def test_record_stats_skips_records_without_samples() -> None:
    stats = record_stats_from_records(
        [{"samples": []}, {"samples": [62.0]}], HEART_RATE_ARTIFACT_CEILING_BPM
    )
    assert stats.record_count == 1
    assert stats.mean == 62.0


def test_record_stats_ci95_from_record_means() -> None:
    # Record means 60 and 70: stdev 7.0711, standard error 5.0, ci 9.8.
    stats = record_stats_from_records(
        [{"samples": [60.0]}, {"samples": [70.0]}], HEART_RATE_ARTIFACT_CEILING_BPM
    )
    assert stats.record_count == 2
    assert stats.mean == 65.0
    assert stats.ci95_half_width == 9.8


def test_respiratory_split_buckets_by_night_window() -> None:
    split = respiratory_night_day_split(
        [
            {"local_time": "04:10:00+03:00", "samples": [14.0]},
            {"local_time": "23:30:00+03:00", "samples": [16.0]},
            {"local_time": "10:00:00+03:00", "samples": [22.0]},
            {"local_time": "08:30:00+03:00", "samples": [26.0]},
        ]
    )
    assert split.night_record_count == 2
    assert split.night_mean == 15.0
    assert split.day_record_count == 2
    assert split.day_mean == 24.0


def test_respiratory_night_window_excludes_the_morning_activity_peak() -> None:
    """08:00 is the peak active hour, so a post-walk reading is not resting-at-night.

    The 14-hour NIGHT_SLEEP_HOURS window exists to match Tractive's timeline
    colouring and takes in that peak.
    """
    split = respiratory_night_day_split([{"local_time": "08:30:00+03:00", "samples": [28.0]}])
    assert split.night_record_count == 0
    assert split.day_record_count == 1


def test_respiratory_split_parses_no_seconds_local_time() -> None:
    split = respiratory_night_day_split([{"local_time": "13:29+03:00", "samples": [20.0]}])
    assert split.day_record_count == 1
    assert split.day_mean == 20.0


def test_respiratory_split_parses_single_digit_hour() -> None:
    split = respiratory_night_day_split([{"local_time": "4:15:00+03:00", "samples": [15.0]}])
    assert split.night_record_count == 1
    assert split.night_mean == 15.0


def test_respiratory_split_skips_unparseable_local_time() -> None:
    split = respiratory_night_day_split(
        [
            {"local_time": "", "samples": [15.0]},
            {"local_time": "abc", "samples": [15.0]},
            {"local_time": "27:00:00+03:00", "samples": [15.0]},
            {"local_time": 915, "samples": [15.0]},
        ]
    )
    assert split.night_record_count == 0
    assert split.day_record_count == 0


def test_respiratory_split_skips_records_without_local_time() -> None:
    split = respiratory_night_day_split([{"samples": [20.0]}])
    assert split.night_record_count == 0
    assert split.day_record_count == 0
    assert split.night_mean is None
    assert split.day_mean is None


def test_respiratory_split_applies_artifact_ceiling() -> None:
    split = respiratory_night_day_split(
        [
            {"local_time": "03:00:00+03:00", "samples": [RESPIRATORY_RATE_ARTIFACT_CEILING + 1]},
            {"local_time": "03:30:00+03:00", "samples": [RESPIRATORY_RATE_ARTIFACT_CEILING]},
        ]
    )
    assert split.night_record_count == 1
    assert split.night_mean == RESPIRATORY_RATE_ARTIFACT_CEILING


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
    assert day_one.resting_heart_rate_records.record_count == 1
    assert day_one.resting_heart_rate_records.mean == 62.0
    assert day_one.resting_heart_rate_records.ci95_half_width is None
    assert day_one.resting_respiratory_rate_records.record_count == 2
    assert day_one.resting_respiratory_rate_records.mean == 17.0
    assert day_one.resting_respiratory_rate_records.ci95_half_width == 1.96
    assert day_one.respiratory_night_day.night_record_count == 1
    assert day_one.respiratory_night_day.night_mean == 16.0
    assert day_one.respiratory_night_day.day_record_count == 1
    assert day_one.respiratory_night_day.day_mean == 18.0
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
    # The RLE starts at local midnight, so the 1h cat-7 chunk lands at local
    # hour 0 (inside the 20:00-09:59 night window) and buckets as night_sleep.
    assert day_two.minutes.night_sleep == 60.0
    assert day_two.minutes.day_sleep == 0.0
    assert day_two.hourly_minutes_by_category == {0: {"night_sleep": 60.0}}
    # Day two has no positions or vitals — assert the zero/empty defaults.
    assert day_two.positions.count == 0
    assert day_two.positions.distance_km == 0.0
    assert day_two.resting_heart_rate_records.record_count == 0
    assert day_two.resting_heart_rate_records.mean is None
    assert day_two.respiratory_night_day.night_record_count == 0
    assert day_two.respiratory_night_day.night_mean is None
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


def test_build_per_day_raises_malformed_error_on_bad_activity_shape() -> None:
    """A valid-JSON activity day missing required keys raises the domain error
    (which routes translate to a 400) rather than a bare KeyError."""
    payloads = GdprExportPayloads(
        activity_data=[{"unexpected": "shape"}],
        position_reports=[],
        hardware_reports=[],
        resting_heart_rates=[],
        resting_respiratory_rates=[],
    )
    with pytest.raises(MalformedTractivePayloadError):
        build_per_day(payloads)


def test_build_per_day_orders_positions_and_charging_by_time() -> None:
    """first/last position time and charge-start counts must be derived
    chronologically, independent of the order the export lists records in."""
    offset_milliseconds = 3 * 3_600_000
    activity_data = [
        {
            "gmtTime": 1_715_731_200_000,  # 2024-05-15 00:00 UTC
            "gmtOffset": offset_milliseconds,
            "activityCategories": [[3600, -1]],
        }
    ]
    # Deliberately shuffled (not chronological).
    position_reports = [
        {
            "time": "2024-05-15T10:00:00Z",
            "latlong": [44.0, 26.0],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
        {
            "time": "2024-05-15T08:00:00Z",
            "latlong": [44.0, 26.0],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
        {
            "time": "2024-05-15T09:00:00Z",
            "latlong": [44.0, 26.0],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
    ]
    hardware_reports = [
        {
            "time": "2024-05-15T10:00:00Z",
            "battery_level": 50,
            "temperature": 20.0,
            "charger_connected": True,
        },
        {
            "time": "2024-05-15T07:00:00Z",
            "battery_level": 80,
            "temperature": 22.0,
            "charger_connected": False,
        },
        {
            "time": "2024-05-15T09:00:00Z",
            "battery_level": 60,
            "temperature": 21.0,
            "charger_connected": False,
        },
        {
            "time": "2024-05-15T08:00:00Z",
            "battery_level": 70,
            "temperature": 21.5,
            "charger_connected": True,
        },
    ]
    payloads = GdprExportPayloads(
        activity_data=activity_data,
        position_reports=position_reports,
        hardware_reports=hardware_reports,
        resting_heart_rates=[],
        resting_respiratory_rates=[],
    )

    [rollup] = build_per_day(payloads)

    assert rollup.positions.first_time == parse_iso("2024-05-15T08:00:00Z")
    assert rollup.positions.last_time == parse_iso("2024-05-15T10:00:00Z")
    # Chronological charger states: off(07) → on(08) → off(09) → on(10) = 2 starts.
    assert rollup.tracker.n_charging_starts == 2


def test_build_per_day_buckets_half_hour_timezone_without_truncation() -> None:
    """A +05:30 offset must not be truncated to 5h — a position 15 min past
    local midnight belongs to the new local day, not the previous one."""
    offset_milliseconds = 5 * 3_600_000 + 30 * 60_000  # +05:30 (e.g. IST)
    activity_data = [
        {
            "gmtTime": 1_715_731_200_000,  # 2024-05-15 00:00 UTC
            "gmtOffset": offset_milliseconds,
            "activityCategories": [[3600, -1]],
        }
    ]
    # 18:45Z + 05:30 = 2024-05-15 00:15 local → belongs to 2024-05-15, not the
    # 14th (which is what a truncated 5h offset would produce: 23:45 on the 14th).
    position_reports = [
        {
            "time": "2024-05-14T18:45:00Z",
            "latlong": [44.0, 26.0],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        }
    ]
    payloads = GdprExportPayloads(
        activity_data=activity_data,
        position_reports=position_reports,
        hardware_reports=[],
        resting_heart_rates=[],
        resting_respiratory_rates=[],
    )

    [rollup] = build_per_day(payloads)
    assert rollup.date == date(2024, 5, 15)
    assert rollup.positions.count == 1


def _home_fix(
    minute: int,
    latitude: float = 44.4488,
    longitude: float = 26.0221,
    hour: int = 6,
) -> dict[str, object]:
    return {
        "time": f"2024-05-15T{hour:02d}:{minute:02d}:00Z",
        "latlong": [latitude, longitude],
        "hori_accuracy": 5,
        "sensor_used": "GNSS",
    }


def _away_fix(minute: int, hour: int = 8) -> dict[str, object]:
    # Roughly 550 m north of the home cluster.
    return {
        "time": f"2024-05-15T{hour:02d}:{minute:02d}:00Z",
        "latlong": [44.4538, 26.0221],
        "hori_accuracy": 5,
        "sensor_used": "GNSS",
    }


def _twelve_home_fixes() -> list[dict[str, object]]:
    return [_home_fix(minute) for minute in range(12)]


def test_derive_home_center_returns_densest_cluster_centroid() -> None:
    home = derive_home_center([*_twelve_home_fixes(), _away_fix(0), _away_fix(10)])
    assert home is not None
    assert home[0] == pytest.approx(44.4488, abs=0.0005)
    assert home[1] == pytest.approx(26.0221, abs=0.0005)


def test_derive_home_center_requires_minimum_fixes() -> None:
    assert derive_home_center([_home_fix(minute) for minute in range(9)]) is None
    assert derive_home_center([]) is None


def test_derive_home_center_ignores_phone_and_inaccurate_fixes() -> None:
    phone_fixes = [{**_home_fix(minute), "sensor_used": "PHONE"} for minute in range(20)]
    inaccurate_fixes = [{**_home_fix(minute), "hori_accuracy": 500} for minute in range(20)]
    assert derive_home_center(phone_fixes) is None
    assert derive_home_center(inaccurate_fixes) is None


def test_detect_outings_builds_one_outing_from_an_away_run() -> None:
    home = (44.4488, 26.0221)
    positions = [
        _home_fix(0),
        _away_fix(0),
        _away_fix(10),
        _away_fix(20),
        _home_fix(50),
    ]
    outings = detect_outings(positions, home)
    assert len(outings) == 1
    outing = outings[0]
    assert outing.duration_minutes == 20.0
    assert outing.fix_count == 3
    assert outing.max_distance_meters == pytest.approx(550, abs=30)


def test_detect_outings_splits_on_a_long_sampling_gap() -> None:
    home = (44.4488, 26.0221)
    positions = [
        _away_fix(0),
        _away_fix(10),
        _away_fix(30),
        _away_fix(40),
    ]
    outings = detect_outings(positions, home)
    assert len(outings) == 2
    assert [outing.duration_minutes for outing in outings] == [10.0, 10.0]


def test_detect_outings_drops_jitter_and_single_fix_runs() -> None:
    home = (44.4488, 26.0221)
    # Chronological: a single away fix bracketed by home fixes, then a two-fix
    # away run lasting under the minimum duration. Both must be discarded.
    positions = [
        _home_fix(55, hour=7),
        _away_fix(0),
        _home_fix(5, hour=8),
        _away_fix(10),
        {**_away_fix(12), "time": "2024-05-15T08:12:30Z"},
        _home_fix(20, hour=8),
    ]
    assert detect_outings(positions, home) == []


def test_detect_outings_sorts_out_of_order_input() -> None:
    home = (44.4488, 26.0221)
    positions = [
        _away_fix(20),
        _away_fix(0),
        _away_fix(10),
    ]
    outings = detect_outings(positions, home)
    assert len(outings) == 1
    assert outings[0].duration_minutes == 20.0


def test_detect_outings_splits_at_exactly_the_gap_threshold() -> None:
    home = (44.4488, 26.0221)
    positions = [
        _away_fix(0),
        _away_fix(10),
        _away_fix(25),
        _away_fix(35),
    ]
    # The 10 to 25 gap is exactly 15 minutes, which splits per the >= rule.
    outings = detect_outings(positions, home)
    assert len(outings) == 2


def test_detect_outings_keeps_a_run_at_exactly_the_minimums() -> None:
    home = (44.4488, 26.0221)
    positions = [_away_fix(0), _away_fix(5)]
    outings = detect_outings(positions, home)
    assert len(outings) == 1
    assert outings[0].duration_minutes == 5.0
    assert outings[0].fix_count == 2


def test_detect_outings_treats_near_boundary_fixes_by_radius() -> None:
    home = (44.4488, 26.0221)
    # ~89m north stays inside the 100m radius; ~111m north is outside.
    inside_fix = {**_home_fix(0, hour=8), "latlong": [44.4496, 26.0221]}
    outside_base = {"latlong": [44.4498, 26.0221], "hori_accuracy": 5, "sensor_used": "GNSS"}
    positions = [
        inside_fix,
        {**outside_base, "time": "2024-05-15T08:10:00Z"},
        {**outside_base, "time": "2024-05-15T08:20:00Z"},
        _home_fix(30, hour=8),
    ]
    outings = detect_outings(positions, home)
    assert len(outings) == 1
    assert outings[0].fix_count == 2


def test_detect_outings_skips_fixes_without_accuracy_or_location() -> None:
    home = (44.4488, 26.0221)
    positions = [
        {**_away_fix(0), "hori_accuracy": None},
        {**_away_fix(10), "latlong": [44.4538]},
        {**_away_fix(20), "latlong": None},
    ]
    assert detect_outings(positions, home) == []


def test_detect_outings_ignores_phone_fixes() -> None:
    home = (44.4488, 26.0221)
    positions = [{**_away_fix(minute), "sensor_used": "PHONE"} for minute in (0, 10, 20)]
    assert detect_outings(positions, home) == []


def test_build_per_day_detects_outings_with_derived_home() -> None:
    activity_day = {
        "gmtTime": 1_715_731_200_000,
        "gmtOffset": 3 * 3_600_000,
        "activityCategories": [[86_400, 6]],
    }
    payloads = GdprExportPayloads(
        activity_data=[activity_day],
        position_reports=[*_twelve_home_fixes(), _away_fix(0), _away_fix(10), _away_fix(20)],
        hardware_reports=[],
        resting_heart_rates=[],
        resting_respiratory_rates=[],
    )
    rollups = build_per_day(payloads)
    assert len(rollups) == 1
    day = rollups[0]
    assert day.home_latitude == pytest.approx(44.4488, abs=0.0005)
    assert day.home_longitude == pytest.approx(26.0221, abs=0.0005)
    assert day.outings.count == 1
    assert day.outings.total_minutes == 20.0
    assert day.outings.entries[0].fix_count == 3


def test_build_per_day_skips_outings_without_enough_home_fixes(
    sample_gdpr_payloads: GdprExportPayloads,
) -> None:
    rollups = build_per_day(sample_gdpr_payloads)
    day_one = rollups[0]
    assert day_one.home_latitude is None
    assert day_one.outings.count is None
    assert day_one.outings.total_minutes is None
    assert day_one.outings.entries == []


def test_sleep_architecture_is_none_without_an_activity_timeline() -> None:
    """No timeline means continuity was never derived, which is not a derived zero."""
    architecture = sleep_architecture_from_activity([])
    assert architecture.longest_bout_minutes is None
    assert architecture.bout_count is None
    assert architecture.fragmentation_index is None


def test_fragmentation_ignores_rest_outside_any_retained_bout() -> None:
    """Adding a nap too short to form a bout must not dilute the index.

    Interruptions are only ever counted inside retained bouts, so dividing by
    every rest minute in the day would make the index fall as rest got more broken.
    """
    broken = [[1200, 6], [300, -1], [1200, 6], [300, -1], [1200, 6]]
    baseline = sleep_architecture_from_activity([*broken, [82_200, 0]])
    with_extra_short_nap = sleep_architecture_from_activity(
        [*broken, [3600, 0], [900, 6], [77_700, 0]]
    )

    assert baseline.fragmentation_index == 10.0
    assert with_extra_short_nap.bout_count == baseline.bout_count
    assert with_extra_short_nap.fragmentation_index == baseline.fragmentation_index


def test_sleep_architecture_full_day_of_rest_is_one_bout() -> None:
    architecture = sleep_architecture_from_activity([[86_400, 6]])
    assert architecture.longest_bout_minutes == 1440.0
    assert architecture.bout_count == 1
    assert architecture.fragmentation_index == 0.0


def test_sleep_architecture_tolerates_brief_arousals_inside_a_bout() -> None:
    # 60min rest, 3min awake, 60min rest, remainder no_signal: one 123min
    # bout with 3 interruption minutes over 2h of rest.
    architecture = sleep_architecture_from_activity(
        [[3600, 6], [180, -1], [3600, 6], [79_020, None]]
    )
    assert architecture.longest_bout_minutes == 123.0
    assert architecture.bout_count == 1
    assert architecture.fragmentation_index == 1.5


def test_sleep_architecture_splits_bouts_on_long_awake_gaps() -> None:
    # 30min rest, 10min awake, 30min rest: the gap exceeds the tolerance so
    # two separate bouts remain.
    architecture = sleep_architecture_from_activity(
        [[1800, 6], [600, -1], [1800, 6], [82_200, None]]
    )
    assert architecture.bout_count == 2
    assert architecture.longest_bout_minutes == 30.0
    assert architecture.fragmentation_index == 0.0


def test_sleep_architecture_never_scores_no_signal_as_sleep() -> None:
    # Rest, then an hour of no_signal, then rest again: the gap ends the
    # first bout instead of bridging it.
    architecture = sleep_architecture_from_activity(
        [[3600, 6], [3600, None], [3600, 6], [75_600, -1]]
    )
    assert architecture.bout_count == 2
    assert architecture.longest_bout_minutes == 60.0


def test_sleep_architecture_drops_bouts_under_the_minimum() -> None:
    architecture = sleep_architecture_from_activity([[600, 6], [85_800, -1]])
    assert architecture.bout_count == 0
    assert architecture.longest_bout_minutes == 0.0
    assert architecture.fragmentation_index is None


def test_sleep_architecture_excludes_trailing_awake_gap_before_no_signal() -> None:
    # 30min rest, 3min awake, then no_signal: the tolerated awake tail must
    # not be counted inside the bout.
    architecture = sleep_architecture_from_activity([[1800, 6], [180, -1], [84_420, None]])
    assert architecture.bout_count == 1
    assert architecture.longest_bout_minutes == 30.0
    assert architecture.fragmentation_index == 0.0


def test_sleep_architecture_trims_trailing_awake_gap_at_end_of_day() -> None:
    # Rest ending 2 awake minutes before midnight: the open bout closes at
    # the last rest minute, not at the end of the day.
    architecture = sleep_architecture_from_activity([[84_480, -1], [1800, 6], [120, -1]])
    assert architecture.bout_count == 1
    assert architecture.longest_bout_minutes == 30.0


def test_sleep_architecture_bridges_two_tolerated_gaps_into_one_bout() -> None:
    # rest 20, awake 5, rest 20, awake 5, rest 20: one 70min bout with 10
    # interruption minutes over 1h of rest.
    architecture = sleep_architecture_from_activity(
        [[1200, 6], [300, -1], [1200, 6], [300, -1], [1200, 6], [82_200, None]]
    )
    assert architecture.bout_count == 1
    assert architecture.longest_bout_minutes == 70.0
    assert architecture.fragmentation_index == 10.0


def test_sleep_architecture_treats_uncovered_tail_as_awake() -> None:
    # An RLE that undershoots the day behaves as if the tail were explicit
    # awake time.
    undershoot = sleep_architecture_from_activity([[1800, 6]])
    explicit = sleep_architecture_from_activity([[1800, 6], [84_600, -1]])
    assert undershoot == explicit
    assert undershoot.bout_count == 1
    assert undershoot.longest_bout_minutes == 30.0


def test_sleep_architecture_without_rest_has_no_fragmentation_index() -> None:
    architecture = sleep_architecture_from_activity([[86_400, -1]])
    assert architecture.bout_count == 0
    assert architecture.longest_bout_minutes == 0.0
    assert architecture.fragmentation_index is None


def test_sleep_architecture_counts_day_naps_as_rest() -> None:
    architecture = sleep_architecture_from_activity([[3600, 7], [82_800, -1]])
    assert architecture.bout_count == 1
    assert architecture.longest_bout_minutes == 60.0


def _activity_day(gmt_time_ms: int, categories: list[list[int | None]]) -> dict[str, object]:
    return {
        "gmtTime": gmt_time_ms,
        "gmtOffset": 0,
        "activityCategories": categories,
    }


def test_overnight_sleep_is_one_bout_not_split_at_midnight() -> None:
    """A 22:30-07:00 sleep is one 8h30m stretch, not a 90m and a 420m stretch.

    Detecting bouts inside a single 1440-minute day cuts the main overnight sleep
    at local midnight, understating the headline every single day.
    """
    day_one_ms = 1_715_731_200_000  # 2024-05-15 00:00 UTC, offset 0
    day_two_ms = day_one_ms + 86_400_000
    architecture = sleep_architecture_by_local_date(
        [
            # awake until 22:30, then rest to midnight
            _activity_day(day_one_ms, [[81_000, -1], [5_400, 6]]),
            # rest until 07:00, then awake
            _activity_day(day_two_ms, [[25_200, 6], [61_200, -1]]),
        ]
    )

    day_two = architecture["2024-05-16"]
    assert day_two.longest_bout_minutes == 510.0
    assert day_two.bout_count == 1
    assert architecture["2024-05-15"].bout_count == 0


def test_bouts_are_not_stitched_across_a_gap_in_the_export() -> None:
    """Non-adjacent days are not adjacent in time, so their minutes must not join."""
    day_one_ms = 1_715_731_200_000
    three_days_later_ms = day_one_ms + 3 * 86_400_000
    architecture = sleep_architecture_by_local_date(
        [
            _activity_day(day_one_ms, [[81_000, -1], [5_400, 6]]),
            _activity_day(three_days_later_ms, [[25_200, 6], [61_200, -1]]),
        ]
    )

    assert architecture["2024-05-15"].longest_bout_minutes == 90.0
    assert architecture["2024-05-18"].longest_bout_minutes == 420.0


def _fix_at(date_str: str, latitude: float, longitude: float, index: int) -> dict[str, object]:
    return {
        "time": f"{date_str}T{index // 60:02d}:{index % 60:02d}:00Z",
        "latlong": [latitude, longitude],
        "hori_accuracy": 5,
        "sensor_used": "GPS",
    }


def test_home_follows_a_relocation_within_the_export() -> None:
    """A single home for the whole batch calls every fix at the new address 'away'."""
    old_home = (44.100, 26.100)
    new_home = (44.500, 26.500)
    positions_by_date: dict[str, list[dict[str, object]]] = {}
    for day in range(1, 11):
        positions_by_date[f"2024-05-{day:02d}"] = [
            _fix_at(f"2024-05-{day:02d}", *old_home, index) for index in range(20)
        ]
    for day in range(20, 31):
        positions_by_date[f"2024-05-{day:02d}"] = [
            _fix_at(f"2024-05-{day:02d}", *new_home, index) for index in range(20)
        ]

    centers = home_center_by_local_date(positions_by_date)

    early = centers["2024-05-05"]
    late = centers["2024-05-25"]
    assert early is not None and late is not None
    assert round(early[0], 2) == 44.10
    assert round(late[0], 2) == 44.50

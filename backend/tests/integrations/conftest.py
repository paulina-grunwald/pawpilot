"""Fixtures shared across integration tests."""

from __future__ import annotations

from typing import Any

import pytest

from app.integrations.tractive.consolidate import GdprExportPayloads


@pytest.fixture
def sample_gdpr_payloads() -> GdprExportPayloads:
    """A tiny but realistic GDPR export covering two days.

    Built by hand so the expected rollup values are easy to predict in tests.
    GMT offset is +03:00 (Bucharest in May, matching the real-world dataset).
    """
    offset_milliseconds = 3 * 3_600_000
    day_one_gmt_ms = 1_715_731_200_000  # 2024-05-15 00:00 UTC → 03:00 local
    day_two_gmt_ms = day_one_gmt_ms + 24 * 3_600_000

    activity_data: list[dict[str, Any]] = [
        {
            "gmtTime": day_one_gmt_ms,
            "gmtOffset": offset_milliseconds,
            # 1h sleep (6) + 30m active (-1) + 30m off (None)
            "activityCategories": [[3600, 6], [1800, -1], [1800, None]],
        },
        {
            "gmtTime": day_two_gmt_ms,
            "gmtOffset": offset_milliseconds,
            # 1h day_sleep (7) only
            "activityCategories": [[3600, 7]],
        },
    ]

    position_reports: list[dict[str, Any]] = [
        # Two collar points 1 km apart on day one, 30 min apart → 2 km/h → kept.
        {
            "time": "2024-05-15T08:00:00Z",
            "latlong": [44.4268, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
        {
            "time": "2024-05-15T08:30:00Z",
            "latlong": [44.4358, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "GPS",
        },
        # Phone point — dropped by sensor filter.
        {
            "time": "2024-05-15T09:00:00Z",
            "latlong": [44.4358, 26.1025],
            "hori_accuracy": 5,
            "sensor_used": "PHONE",
        },
    ]

    hardware_reports: list[dict[str, Any]] = [
        {
            "time": "2024-05-15T07:00:00Z",
            "battery_level": 80,
            "temperature": 22.5,
            "charger_connected": False,
        },
        {
            "time": "2024-05-15T20:00:00Z",
            "battery_level": 60,
            "temperature": 21.0,
            "charger_connected": True,
        },
    ]

    resting_heart_rates: list[dict[str, Any]] = [
        {"local_date": "2024-05-15", "records": [{"samples": [60.0, 62.0, 64.0]}]},
    ]

    resting_respiratory_rates: list[dict[str, Any]] = [
        {"local_date": "2024-05-15", "records": [{"samples": [16.0, 18.0]}]},
    ]

    return GdprExportPayloads(
        activity_data=activity_data,
        position_reports=position_reports,
        hardware_reports=hardware_reports,
        resting_heart_rates=resting_heart_rates,
        resting_respiratory_rates=resting_respiratory_rates,
    )

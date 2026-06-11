"""Tests for the Markdown rendering of per-day rollups."""

from __future__ import annotations

from app.integrations.tractive.consolidate import GdprExportPayloads, build_per_day
from app.integrations.tractive.markdown import render_summary
from app.integrations.tractive.schemas import (
    ActivityMinutes,
    PerDayRollup,
    PositionSummary,
    TrackerSummary,
    VitalStats,
)


def test_render_summary_includes_all_four_section_headers(
    sample_gdpr_payloads: GdprExportPayloads,
) -> None:
    markdown = render_summary(build_per_day(sample_gdpr_payloads))
    assert "## Activity & sleep" in markdown
    assert "## Vitals" in markdown
    assert "## Movement" in markdown
    assert "## Tracker" in markdown


def test_render_summary_formats_minutes_under_an_hour_as_plain_minutes() -> None:
    rollup = PerDayRollup(
        date="2024-05-15",  # type: ignore[arg-type]
        minutes=ActivityMinutes(active=45.0),
        hourly_minutes_by_category={},
        resting_heart_rate=VitalStats(n_samples=0),
        resting_respiratory_rate=VitalStats(n_samples=0),
        positions=PositionSummary(count=0, distance_km=0.0, segments_counted=0, segments_dropped=0),
        tracker=TrackerSummary(),
    )
    markdown = render_summary([rollup])
    assert "| 45m |" in markdown


def test_render_summary_formats_minutes_over_an_hour_as_hours_and_minutes() -> None:
    rollup = PerDayRollup(
        date="2024-05-15",  # type: ignore[arg-type]
        minutes=ActivityMinutes(night_sleep=125.0),
        hourly_minutes_by_category={},
        resting_heart_rate=VitalStats(n_samples=0),
        resting_respiratory_rate=VitalStats(n_samples=0),
        positions=PositionSummary(count=0, distance_km=0.0, segments_counted=0, segments_dropped=0),
        tracker=TrackerSummary(),
    )
    markdown = render_summary([rollup])
    assert "2h 05m" in markdown


def test_render_summary_shows_em_dash_for_missing_vitals_and_tracker() -> None:
    rollup = PerDayRollup(
        date="2024-05-15",  # type: ignore[arg-type]
        minutes=ActivityMinutes(),
        hourly_minutes_by_category={},
        resting_heart_rate=VitalStats(n_samples=0),
        resting_respiratory_rate=VitalStats(n_samples=0),
        positions=PositionSummary(count=0, distance_km=0.0, segments_counted=0, segments_dropped=0),
        tracker=TrackerSummary(),
    )
    markdown = render_summary([rollup])
    # vitals row has two em dashes (HR + RR); tracker row has two more (battery + temp)
    assert markdown.count("—") >= 4

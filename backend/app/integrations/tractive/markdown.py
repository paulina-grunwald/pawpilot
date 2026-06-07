"""Render a list of PerDayRollup as a human-readable Markdown summary."""

from __future__ import annotations

from app.integrations.tractive.schemas import PerDayRollup, VitalStats


def render_summary(rollups: list[PerDayRollup]) -> str:
    """Format the per-day rollups as a four-table Markdown report."""
    lines = [
        "# Per-day rollup",
        "",
        (
            f"_{len(rollups)} days from Tractive GDPR export. Categories are best-guess; "
            "verify against hourly distribution._"
        ),
        "",
        "## Activity & sleep",
        "",
        "| Date | Active | Night sleep | Day sleep | Low int. | Moderate | No signal |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rollup in rollups:
        minutes = rollup.minutes
        lines.append(
            f"| {rollup.date} | "
            f"{_format_hours_minutes(minutes.active)} | "
            f"{_format_hours_minutes(minutes.night_sleep)} | "
            f"{_format_hours_minutes(minutes.day_sleep)} | "
            f"{minutes.low_intensity:.0f}m | "
            f"{minutes.moderate:.0f}m | "
            f"{_format_hours_minutes(minutes.no_signal)} |"
        )

    lines += ["", "## Vitals", "", "| Date | Resting HR | Resting RR |", "|---|---|---|"]
    for rollup in rollups:
        lines.append(
            f"| {rollup.date} | "
            f"{_format_vital(rollup.resting_heart_rate, 'bpm')} | "
            f"{_format_vital(rollup.resting_respiratory_rate, 'rpm')} |"
        )

    lines += [
        "",
        "## Movement",
        "",
        "| Date | Distance walked | GPS points | Segments used |",
        "|---|---:|---:|---:|",
    ]
    for rollup in rollups:
        positions = rollup.positions
        lines.append(
            f"| {rollup.date} | {positions.distance_km} km | "
            f"{positions.count} | "
            f"{positions.segments_counted} (dropped {positions.segments_dropped}) |"
        )

    lines += [
        "",
        "## Tracker",
        "",
        "| Date | Battery | Temperature | Charge starts |",
        "|---|---|---|---:|",
    ]
    for rollup in rollups:
        tracker = rollup.tracker
        battery_text = (
            f"{tracker.battery_min}–{tracker.battery_max}%"  # noqa: RUF001
            if tracker.battery_min is not None
            else "—"
        )
        temperature_text = (
            f"{_compact(tracker.temperature_min)}–"  # noqa: RUF001
            f"{_compact(tracker.temperature_max)}°C"
            if tracker.temperature_min is not None
            else "—"
        )
        lines.append(
            f"| {rollup.date} | {battery_text} | {temperature_text} | {tracker.n_charging_starts} |"
        )

    return "\n".join(lines) + "\n"


def _format_hours_minutes(minutes: float) -> str:
    if minutes < 60:
        return f"{minutes:.0f}m"
    return f"{int(minutes // 60)}h {int(minutes % 60):02d}m"


def _format_vital(stats: VitalStats, unit: str) -> str:
    if stats.n_samples == 0:
        return "—"
    return (
        f"{stats.mean} {unit} (n={stats.n_samples}, "
        f"range {_compact(stats.min)}–{_compact(stats.max)})"  # noqa: RUF001
    )


def _compact(value: float | int | None) -> str:
    """Drop trailing `.0` from floats that are mathematically integers."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)

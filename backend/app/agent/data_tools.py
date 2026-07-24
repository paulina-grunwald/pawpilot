"""The dog-data tools: read this dog's own tracker metrics from the database.

Two tools cover every metric in the registry. `get_dog_metric` takes the metric and
the aggregation as arguments rather than encoding them in tool names, which is what
keeps this at two tools instead of one per metric per aggregation.
`get_dog_health_snapshot` averages everything at once, so an open question like
"how is she doing?" costs one call rather than one per metric.

Both are bound per run to a `PetDataReader` already scoped to the owner's pet, so
the model chooses only what to read and over what window, never whose data. The
tools are async-only because the reader is a database query and a DB-backed run is
always driven by ainvoke.

Every average, extreme, and coverage count is computed here rather than handed to
the model as raw rows: a language model should never be doing this arithmetic.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Protocol

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel

from app.agent.metric_registry import (
    METRIC_SPECS,
    DogMetric,
    MetricAggregation,
    MetricSpec,
    metric_spec,
    render_metric_value,
)
from app.integrations.tractive.read_service import MetricDayRow

DEFAULT_WINDOW_DAYS = 7
MAX_WINDOW_DAYS = 365

METRIC_TOOL_NAME = "get_dog_metric"
SNAPSHOT_TOOL_NAME = "get_dog_health_snapshot"

_METRIC_TOOL_DESCRIPTION = (
    "Read one measured metric from THIS dog's activity tracker. Use it for any "
    "question about what the dog's own tracker actually recorded, for example "
    "'how much did she sleep this week?', 'what was his resting heart rate "
    "yesterday?', or 'which day did she walk furthest?'.\n"
    "metric: which measurable to read. One of: " + ", ".join(sorted(DogMetric)) + ".\n"
    "aggregation: how to summarize it. 'average' over the window (the default), "
    "'on_date' for one specific day, 'daily_series' for every day listed out, "
    "'highest_day' or 'lowest_day' for the extreme day and its date.\n"
    f"days: how far back to look, default {DEFAULT_WINDOW_DAYS}, at most "
    f"{MAX_WINDOW_DAYS}. Ignored when aggregation is 'on_date'.\n"
    "date: required when aggregation is 'on_date', as ISO YYYY-MM-DD.\n"
    "Returns the figure with its units, how many days actually had data, and any "
    "caveat that applies to that metric. Report the caveat when you use the number."
)

_SNAPSHOT_TOOL_DESCRIPTION = (
    "Read every tracker metric for THIS dog at once, each averaged over a recent "
    "window. Use it for broad questions about how the dog is doing generally, for "
    "example 'how is Luna this week?' or 'is anything off with him lately?', instead "
    "of calling get_dog_metric once per metric. Pass the number of days to look back "
    f"(default {DEFAULT_WINDOW_DAYS}, at most {MAX_WINDOW_DAYS}). Returns one line "
    "per metric with its units and coverage."
)


class PetDataReader(Protocol):
    """Reads one already-scoped dog's metric days: a recent window, or one day."""

    async def fetch_window(self, days: int) -> list[MetricDayRow]: ...

    async def fetch_on_date(self, day: date_type) -> MetricDayRow | None: ...


class MetricSample(BaseModel):
    """One day's value for a single metric, with the reading count behind it."""

    date: date_type
    value: float
    reading_count: int | None
    uncertainty: float | None


def collect_samples(rows: list[MetricDayRow], spec: MetricSpec) -> list[MetricSample]:
    """Pull one metric out of the day rows, dropping days where it was not recorded.

    Coverage is counted per metric, not per row: a day can have a rollup and still
    have no heart-rate reading, and reporting that day as covered would overstate
    how much the number rests on.
    """
    samples: list[MetricSample] = []
    for row in rows:
        value = getattr(row, spec.value_field)
        if value is None:
            continue
        samples.append(
            MetricSample(
                date=row.date,
                value=float(value),
                reading_count=(
                    getattr(row, spec.sample_count_field)
                    if spec.sample_count_field is not None
                    else None
                ),
                uncertainty=(
                    getattr(row, spec.uncertainty_field)
                    if spec.uncertainty_field is not None
                    else None
                ),
            )
        )
    return samples


def clamp_days(days: int) -> int:
    """Keep the look-back window within a sane range whatever the model asks for."""
    return max(1, min(days, MAX_WINDOW_DAYS))


def parse_iso_date(value: str) -> date_type | None:
    """Parse an ISO ``YYYY-MM-DD`` string, or None when the model sent something else."""
    try:
        return date_type.fromisoformat(value.strip())
    except ValueError:
        return None


def _render_reading_basis(sample: MetricSample, spec: MetricSpec) -> str:
    """Render how many readings a single day's vital rests on, and how tight they were."""
    if sample.reading_count is None:
        return ""
    parts = [f"from {sample.reading_count} reading{'s' if sample.reading_count != 1 else ''}"]
    if sample.uncertainty is not None:
        parts.append(f"give or take {render_metric_value(sample.uncertainty, spec.unit)}")
    return f" ({', '.join(parts)})"


def _coverage_note(days_with_data: int, days_requested: int) -> str:
    """State the denominator plainly so an average is never read as a full window."""
    if days_with_data == days_requested:
        return f"all {days_requested} days had data"
    return f"only {days_with_data} of the {days_requested} days had data"


def render_average(samples: list[MetricSample], spec: MetricSpec, days_requested: int) -> str:
    """Average a metric over the window and say what the average rests on."""
    if not samples:
        return _no_data_over_window(spec, days_requested)
    average = sum(sample.value for sample in samples) / len(samples)
    return (
        f"Average {spec.label}: {render_metric_value(average, spec.unit)}/day over the "
        f"last {days_requested} days ({_coverage_note(len(samples), days_requested)}, "
        f"{samples[0].date} to {samples[-1].date}).\n"
        f"{spec.description}"
    )


def render_on_date(sample: MetricSample | None, spec: MetricSpec, day: date_type) -> str:
    """Render one day's value for a metric, or say the day has nothing recorded."""
    if sample is None:
        return f"No {spec.label} is recorded for this dog on {day}."
    return (
        f"{spec.label.capitalize()} on {day}: "
        f"{render_metric_value(sample.value, spec.unit)}"
        f"{_render_reading_basis(sample, spec)}.\n"
        f"{spec.description}"
    )


def render_daily_series(samples: list[MetricSample], spec: MetricSpec, days_requested: int) -> str:
    """List a metric day by day, so the model can spot a trend without inventing one."""
    if not samples:
        return _no_data_over_window(spec, days_requested)
    lines = [
        f"- {sample.date}: {render_metric_value(sample.value, spec.unit)}" for sample in samples
    ]
    header = (
        f"{spec.label.capitalize()} by day over the last {days_requested} days "
        f"({_coverage_note(len(samples), days_requested)}):"
    )
    return f"{header}\n" + "\n".join(lines) + f"\n{spec.description}"


def render_extreme(
    samples: list[MetricSample], spec: MetricSpec, days_requested: int, *, highest: bool
) -> str:
    """Render the highest or lowest day for a metric, naming the date."""
    if not samples:
        return _no_data_over_window(spec, days_requested)
    chosen = (
        max(samples, key=lambda sample: sample.value)
        if highest
        else min(samples, key=lambda sample: sample.value)
    )
    superlative = "Highest" if highest else "Lowest"
    return (
        f"{superlative} {spec.label} in the last {days_requested} days was on "
        f"{chosen.date}: {render_metric_value(chosen.value, spec.unit)}"
        f"{_render_reading_basis(chosen, spec)} "
        f"({_coverage_note(len(samples), days_requested)}).\n"
        f"{spec.description}"
    )


def _no_data_over_window(spec: MetricSpec, days_requested: int) -> str:
    return f"No {spec.label} is recorded for this dog in the last {days_requested} days."


def render_snapshot(rows: list[MetricDayRow], days_requested: int) -> str:
    """Average every metric over the window, one line each."""
    if not rows:
        return f"No tracker data is recorded for this dog in the last {days_requested} days."
    lines: list[str] = []
    for spec in METRIC_SPECS.values():
        samples = collect_samples(rows, spec)
        if not samples:
            lines.append(f"- {spec.label}: no data")
            continue
        average = sum(sample.value for sample in samples) / len(samples)
        lines.append(
            f"- {spec.label}: {render_metric_value(average, spec.unit)}"
            f" (from {len(samples)} day{'s' if len(samples) != 1 else ''})"
        )
    return (
        f"Tracker averages over the last {days_requested} days "
        f"({_coverage_note(len(rows), days_requested)}, {rows[0].date} to {rows[-1].date}):\n"
        + "\n".join(lines)
        + "\nCounts of outings are a floor, and sleep figures describe how consolidated "
        "rest was, never clinical sleep stages."
    )


def build_pet_data_tools(reader: PetDataReader, invoked_tools: list[str]) -> list[BaseTool]:
    """Build the dog-data tools bound to one run's owner-scoped ``reader``."""

    async def get_dog_metric(
        metric: DogMetric,
        aggregation: MetricAggregation = MetricAggregation.AVERAGE,
        days: int = DEFAULT_WINDOW_DAYS,
        date: str | None = None,
    ) -> str:
        invoked_tools.append(METRIC_TOOL_NAME)
        spec = metric_spec(metric)

        if aggregation is MetricAggregation.ON_DATE:
            if date is None:
                return (
                    f"The '{aggregation}' aggregation needs a date. Call again with "
                    "date set to the day you want, in ISO format YYYY-MM-DD."
                )
            day = parse_iso_date(date)
            if day is None:
                return f"'{date}' is not a valid date. Provide the date in ISO format YYYY-MM-DD."
            row = await reader.fetch_on_date(day)
            samples = collect_samples([row] if row is not None else [], spec)
            return render_on_date(samples[0] if samples else None, spec, day)

        window = clamp_days(days)
        samples = collect_samples(await reader.fetch_window(window), spec)
        match aggregation:
            case MetricAggregation.AVERAGE:
                return render_average(samples, spec, window)
            case MetricAggregation.DAILY_SERIES:
                return render_daily_series(samples, spec, window)
            case MetricAggregation.HIGHEST_DAY:
                return render_extreme(samples, spec, window, highest=True)
            case MetricAggregation.LOWEST_DAY:
                return render_extreme(samples, spec, window, highest=False)
            case MetricAggregation.ON_DATE:  # pragma: no cover - handled above
                raise AssertionError("on_date is handled before the window is fetched")

    async def get_dog_health_snapshot(days: int = DEFAULT_WINDOW_DAYS) -> str:
        invoked_tools.append(SNAPSHOT_TOOL_NAME)
        window = clamp_days(days)
        return render_snapshot(await reader.fetch_window(window), window)

    return [
        StructuredTool.from_function(
            coroutine=get_dog_metric,
            name=METRIC_TOOL_NAME,
            description=_METRIC_TOOL_DESCRIPTION,
        ),
        StructuredTool.from_function(
            coroutine=get_dog_health_snapshot,
            name=SNAPSHOT_TOOL_NAME,
            description=_SNAPSHOT_TOOL_DESCRIPTION,
        ),
    ]

"""The catalogue of dog metrics the agent can read from its tracker.

Metric and aggregation are arguments, not tool names. One tool over this registry
replaces what would otherwise be a tool per metric per aggregation, which is where
tool selection starts to break down.

Every spec is declarative: it names the fields it reads on a `MetricDayRow` rather
than carrying a function, so the registry stays plain data and the extraction is a
single generic getattr. Adding a metric is one entry here.

Each spec also carries the caveat that must reach the owner. The tracker measures
some of these far less precisely than a bare number suggests, and the descriptions
are what stop the agent presenting a floor as an exact tally.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

_MINUTES_PER_HOUR = 60.0


class DogMetric(StrEnum):
    """A measurable the tracker records about the dog itself."""

    TOTAL_SLEEP = "total_sleep"
    NIGHT_SLEEP = "night_sleep"
    DAY_SLEEP = "day_sleep"
    LONGEST_SLEEP_BOUT = "longest_sleep_bout"
    SLEEP_BOUT_COUNT = "sleep_bout_count"
    SLEEP_FRAGMENTATION = "sleep_fragmentation"
    ACTIVE_TIME = "active_time"
    MODERATE_ACTIVITY = "moderate_activity"
    LOW_INTENSITY_ACTIVITY = "low_intensity_activity"
    NO_SIGNAL_TIME = "no_signal_time"
    RESTING_HEART_RATE = "resting_heart_rate"
    RESTING_RESPIRATORY_RATE = "resting_respiratory_rate"
    NIGHT_RESTING_RESPIRATORY_RATE = "night_resting_respiratory_rate"
    DAY_RESTING_RESPIRATORY_RATE = "day_resting_respiratory_rate"
    OUTINGS_COUNT = "outings_count"
    OUTINGS_TOTAL_TIME = "outings_total_time"
    WALKING_DISTANCE = "walking_distance"


class MetricAggregation(StrEnum):
    """How to summarize a metric over the requested window."""

    AVERAGE = "average"
    ON_DATE = "on_date"
    DAILY_SERIES = "daily_series"
    HIGHEST_DAY = "highest_day"
    LOWEST_DAY = "lowest_day"


class MetricUnit(StrEnum):
    """How a metric's number is rendered back to the owner."""

    DURATION = "duration"
    COUNT = "count"
    BEATS_PER_MINUTE = "beats_per_minute"
    BREATHS_PER_MINUTE = "breaths_per_minute"
    KILOMETERS = "kilometers"
    INDEX = "index"


class MetricSpec(BaseModel):
    """One metric: where to read it, how to render it, and what to caveat.

    ``value_field`` and friends name attributes on a `MetricDayRow`. Keeping them
    as names rather than accessor functions means the registry is inspectable data
    that a test can walk, and there is exactly one code path that reads a value.

    ``sample_count_field`` and ``uncertainty_field`` are set only for the vitals,
    which are averaged from a handful of measurement events per day. Reporting a
    resting heart rate without saying it came from three readings invites the owner
    to trust it more than it deserves.
    """

    label: str
    unit: MetricUnit
    value_field: str
    sample_count_field: str | None = None
    uncertainty_field: str | None = None
    description: str


METRIC_SPECS: dict[DogMetric, MetricSpec] = {
    DogMetric.TOTAL_SLEEP: MetricSpec(
        label="total sleep",
        unit=MetricUnit.DURATION,
        value_field="total_sleep_hours",
        description="All sleep in the day, night plus daytime naps.",
    ),
    DogMetric.NIGHT_SLEEP: MetricSpec(
        label="night sleep",
        unit=MetricUnit.DURATION,
        value_field="night_sleep_hours",
        description="Sleep inside the overnight window (20:00 to 09:59 local).",
    ),
    DogMetric.DAY_SLEEP: MetricSpec(
        label="daytime sleep",
        unit=MetricUnit.DURATION,
        value_field="day_sleep_hours",
        description="Naps outside the overnight window.",
    ),
    DogMetric.LONGEST_SLEEP_BOUT: MetricSpec(
        label="longest unbroken sleep",
        unit=MetricUnit.DURATION,
        value_field="longest_sleep_bout_hours",
        description=(
            "The longest single stretch of unbroken rest. Describes how consolidated "
            "the sleep was, never a clinical sleep stage: the tracker cannot see deep "
            "or light sleep. A day with long no-signal stretches understates this."
        ),
    ),
    DogMetric.SLEEP_BOUT_COUNT: MetricSpec(
        label="sleep bouts",
        unit=MetricUnit.COUNT,
        value_field="sleep_bout_count",
        description=(
            "How many separate stretches of rest made up the day's sleep. More bouts "
            "for the same total sleep means more broken rest."
        ),
    ),
    DogMetric.SLEEP_FRAGMENTATION: MetricSpec(
        label="sleep fragmentation",
        unit=MetricUnit.INDEX,
        value_field="sleep_fragmentation_index",
        description=(
            "Awake interruptions per hour of rest. Higher means more broken sleep. "
            "Descriptive only, not a clinical sleep-quality score."
        ),
    ),
    DogMetric.ACTIVE_TIME: MetricSpec(
        label="active time",
        unit=MetricUnit.DURATION,
        value_field="active_hours",
        description="Time the tracker scored as active movement.",
    ),
    DogMetric.MODERATE_ACTIVITY: MetricSpec(
        label="moderate activity",
        unit=MetricUnit.DURATION,
        value_field="moderate_hours",
        description="Time at moderate intensity.",
    ),
    DogMetric.LOW_INTENSITY_ACTIVITY: MetricSpec(
        label="low-intensity activity",
        unit=MetricUnit.DURATION,
        value_field="low_intensity_hours",
        description="Time at low intensity: pottering rather than resting or exercising.",
    ),
    DogMetric.NO_SIGNAL_TIME: MetricSpec(
        label="no-signal time",
        unit=MetricUnit.DURATION,
        value_field="no_signal_hours",
        description=(
            "Time the collar recorded nothing, usually off the dog or charging. High "
            "no-signal time means every other metric for that day is undercounted."
        ),
    ),
    DogMetric.RESTING_HEART_RATE: MetricSpec(
        label="resting heart rate",
        unit=MetricUnit.BEATS_PER_MINUTE,
        value_field="resting_heart_rate_bpm",
        sample_count_field="resting_heart_rate_reading_count",
        uncertainty_field="resting_heart_rate_ci95_half_width",
        description=(
            "Average resting heart rate across the day's measurement events. Readings "
            "taken while the dog was moving are dropped, so some days have very few."
        ),
    ),
    DogMetric.RESTING_RESPIRATORY_RATE: MetricSpec(
        label="resting respiratory rate",
        unit=MetricUnit.BREATHS_PER_MINUTE,
        value_field="resting_respiratory_rate_per_minute",
        sample_count_field="resting_respiratory_rate_reading_count",
        uncertainty_field="resting_respiratory_rate_ci95_half_width",
        description="Average resting breathing rate across the day's measurement events.",
    ),
    DogMetric.NIGHT_RESTING_RESPIRATORY_RATE: MetricSpec(
        label="night resting respiratory rate",
        unit=MetricUnit.BREATHS_PER_MINUTE,
        value_field="night_resting_respiratory_rate_per_minute",
        sample_count_field="night_resting_respiratory_rate_reading_count",
        description=(
            "Resting breathing rate measured overnight. This is the reading vets ask "
            "owners to watch at home, so prefer it over the all-day figure when the "
            "question is about breathing. Descriptive only, not a diagnosis."
        ),
    ),
    DogMetric.DAY_RESTING_RESPIRATORY_RATE: MetricSpec(
        label="daytime resting respiratory rate",
        unit=MetricUnit.BREATHS_PER_MINUTE,
        value_field="day_resting_respiratory_rate_per_minute",
        sample_count_field="day_resting_respiratory_rate_reading_count",
        description="Resting breathing rate measured outside the overnight window.",
    ),
    DogMetric.OUTINGS_COUNT: MetricSpec(
        label="outings",
        unit=MetricUnit.COUNT,
        value_field="outings_count",
        description=(
            "Walks or trips away from home, detected from GPS. The count is a floor: "
            "sampling gaps and collar-off time can hide whole outings, so zero detected "
            "does not mean the dog never left home. A walk over midnight counts on both days."
        ),
    ),
    DogMetric.OUTINGS_TOTAL_TIME: MetricSpec(
        label="time out of the house",
        unit=MetricUnit.DURATION,
        value_field="outings_total_hours",
        description=(
            "Total time away from home across the day's outings. Measured first to last "
            "away fix, so the legs of the walk near home are cut off. Treat as a floor."
        ),
    ),
    DogMetric.WALKING_DISTANCE: MetricSpec(
        label="distance travelled",
        unit=MetricUnit.KILOMETERS,
        value_field="walking_distance_km",
        description=(
            "Distance from GPS fixes. Undercounts indoor movement and short trips, and "
            "depends on how often the collar got a fix."
        ),
    ),
}


def format_duration_hours(hours: float) -> str:
    """Render decimal hours as `Xh Ym`, matching the dashboard's sleep graph.

    The graph labels every duration in hours and whole minutes, so the agent uses
    the same shape: an owner comparing "11.16 hours" against "11h 10m" reads them as
    two different numbers even though they are the same value.
    """
    minutes = max(0, round(hours * _MINUTES_PER_HOUR))
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes // 60}h {minutes % 60:02d}m"


def render_metric_value(value: float, unit: MetricUnit) -> str:
    """Render one metric value in its own unit."""
    match unit:
        case MetricUnit.DURATION:
            return format_duration_hours(value)
        case MetricUnit.COUNT:
            return str(round(value)) if value == round(value) else f"{value:.1f}"
        case MetricUnit.BEATS_PER_MINUTE:
            return f"{value:.0f} bpm"
        case MetricUnit.BREATHS_PER_MINUTE:
            return f"{value:.0f} breaths/min"
        case MetricUnit.KILOMETERS:
            return f"{value:.2f} km"
        case MetricUnit.INDEX:
            return f"{value:.2f}"


_PER_DAY_UNITS = frozenset({MetricUnit.DURATION, MetricUnit.COUNT, MetricUnit.KILOMETERS})


def render_window_average(value: float, unit: MetricUnit) -> str:
    rendered = render_metric_value(value, unit)
    return f"{rendered}/day" if unit in _PER_DAY_UNITS else rendered


def metric_spec(metric: DogMetric) -> MetricSpec:
    """Return the spec for ``metric``. Every `DogMetric` has one by construction."""
    return METRIC_SPECS[metric]

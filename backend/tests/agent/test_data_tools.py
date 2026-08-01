"""Tests for the metric tools built by `build_pet_data_tools`.

Everything here runs against a `FakePetDataReader`, so aggregation, rendering, day
clamping, and invocation logging are verified with no database and no network.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, ValidationError

from app.agent.data_tools import (
    DEFAULT_WINDOW_DAYS,
    MAX_WINDOW_DAYS,
    METRIC_TOOL_NAME,
    SNAPSHOT_TOOL_NAME,
    build_pet_data_tools,
    clamp_days,
    collect_samples,
    parse_iso_date,
)
from app.agent.fakes import FakePetDataReader
from app.agent.metric_registry import (
    METRIC_SPECS,
    DogMetric,
    MetricAggregation,
    MetricUnit,
    format_duration_hours,
    metric_spec,
    render_metric_value,
)
from app.integrations.tractive.read_service import MetricDayRow


def _row(day: date, **overrides: object) -> MetricDayRow:
    """A fully-populated metric day, overridable per test."""
    values: dict[str, object] = {
        "date": day,
        "total_sleep_hours": 8.0,
        "night_sleep_hours": 6.5,
        "day_sleep_hours": 1.5,
        "longest_sleep_bout_hours": 3.0,
        "sleep_bout_count": 4,
        "sleep_fragmentation_index": 1.25,
        "active_hours": 2.0,
        "moderate_hours": 1.0,
        "low_intensity_hours": 3.0,
        "no_signal_hours": 0.5,
        "resting_heart_rate_bpm": 68.0,
        "resting_heart_rate_reading_count": 12,
        "resting_heart_rate_ci95_half_width": 3.0,
        "resting_respiratory_rate_per_minute": 22.0,
        "resting_respiratory_rate_reading_count": 9,
        "resting_respiratory_rate_ci95_half_width": 2.0,
        "night_resting_respiratory_rate_per_minute": 20.0,
        "night_resting_respiratory_rate_reading_count": 5,
        "day_resting_respiratory_rate_per_minute": 24.0,
        "day_resting_respiratory_rate_reading_count": 4,
        "outings_count": 3,
        "outings_total_hours": 1.5,
        "walking_distance_km": 4.2,
    }
    values.update(overrides)
    return MetricDayRow.model_validate(values)


def _build(rows: list[MetricDayRow]) -> tuple[StructuredTool, FakePetDataReader, list[str]]:
    reader = FakePetDataReader(rows)
    invoked_tools: list[str] = []
    tools = build_pet_data_tools(reader, invoked_tools)
    tool = tools[0]
    assert isinstance(tool, StructuredTool)
    return tool, reader, invoked_tools


def _build_snapshot(rows: list[MetricDayRow]) -> tuple[StructuredTool, list[str]]:
    invoked_tools: list[str] = []
    tools = build_pet_data_tools(FakePetDataReader(rows), invoked_tools)
    tool = tools[1]
    assert isinstance(tool, StructuredTool)
    return tool, invoked_tools


async def _invoke(tool: StructuredTool, **arguments: object) -> str:
    coroutine = tool.coroutine
    assert coroutine is not None
    result = await coroutine(**arguments)
    assert isinstance(result, str)
    return result


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


def test_every_metric_has_a_spec() -> None:
    """A metric the model can name must always resolve to a spec."""
    assert set(METRIC_SPECS) == set(DogMetric)


def test_every_spec_reads_a_real_field_on_a_metric_day_row() -> None:
    """The registry addresses row fields by name, so every name must exist."""
    row = _row(date(2026, 5, 14))
    for metric, spec in METRIC_SPECS.items():
        assert hasattr(row, spec.value_field), f"{metric} value_field"
        for optional_field in (spec.sample_count_field, spec.uncertainty_field):
            if optional_field is not None:
                assert hasattr(row, optional_field), f"{metric} {optional_field}"


def test_every_spec_has_a_label_and_description() -> None:
    for spec in METRIC_SPECS.values():
        assert spec.label.strip()
        assert spec.description.strip()


def test_every_unit_renders() -> None:
    for unit in MetricUnit:
        assert render_metric_value(1.5, unit).strip()


# --------------------------------------------------------------------------- #
# Duration formatting (carried over: these are the dashboard's own figures)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("hours", "expected"),
    [
        # The exact values from the dashboard's Jul 13 sleep-split bar: the agent
        # must read these back as the graph labels them, not as decimal hours.
        (11.16, "11h 10m"),
        (6.66, "6h 40m"),
        (17.83, "17h 50m"),
        (8.0, "8h 00m"),
        (6.5, "6h 30m"),
        (0.0, "0m"),
        (0.5, "30m"),
        (0.99, "59m"),
        (1.0, "1h 00m"),
    ],
)
def test_format_duration_matches_graph_hours_and_minutes(hours: float, expected: str) -> None:
    assert format_duration_hours(hours) == expected


def test_format_duration_clamps_negative_hours_to_zero() -> None:
    assert format_duration_hours(-1.0) == "0m"


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (68.4, MetricUnit.BEATS_PER_MINUTE, "68 bpm"),
        (22.0, MetricUnit.BREATHS_PER_MINUTE, "22 breaths/min"),
        (4.216, MetricUnit.KILOMETERS, "4.22 km"),
        (3.0, MetricUnit.COUNT, "3"),
        (1.25, MetricUnit.INDEX, "1.25"),
    ],
)
def test_render_metric_value_per_unit(value: float, unit: MetricUnit, expected: str) -> None:
    assert render_metric_value(value, unit) == expected


# --------------------------------------------------------------------------- #
# Per-metric coverage
# --------------------------------------------------------------------------- #


def test_collect_samples_skips_days_where_the_metric_was_not_recorded() -> None:
    """A day can have a rollup and still have no vitals; it must not count as covered."""
    rows = [
        _row(date(2026, 5, 14), resting_heart_rate_bpm=70.0),
        _row(date(2026, 5, 15), resting_heart_rate_bpm=None),
        _row(date(2026, 5, 16), resting_heart_rate_bpm=66.0),
    ]
    samples = collect_samples(rows, metric_spec(DogMetric.RESTING_HEART_RATE))
    assert [sample.date for sample in samples] == [date(2026, 5, 14), date(2026, 5, 16)]


def test_collect_samples_carries_reading_count_and_uncertainty_for_vitals() -> None:
    samples = collect_samples([_row(date(2026, 5, 14))], metric_spec(DogMetric.RESTING_HEART_RATE))
    assert samples[0].reading_count == 12
    assert samples[0].uncertainty == 3.0


def test_collect_samples_leaves_reading_count_unset_for_non_vitals() -> None:
    samples = collect_samples([_row(date(2026, 5, 14))], metric_spec(DogMetric.TOTAL_SLEEP))
    assert samples[0].reading_count is None
    assert samples[0].uncertainty is None


# --------------------------------------------------------------------------- #
# Aggregations
# --------------------------------------------------------------------------- #


async def test_average_reports_figure_coverage_and_range() -> None:
    rows = [
        _row(date(2026, 5, 14), total_sleep_hours=8.0),
        _row(date(2026, 5, 15), total_sleep_hours=10.0),
    ]
    tool, _reader, invoked_tools = _build(rows)

    result = await _invoke(tool, metric=DogMetric.TOTAL_SLEEP, days=2)

    assert "Average total sleep: 9h 00m/day" in result
    assert "all 2 days had data" in result
    assert "2026-05-14 to 2026-05-15" in result
    assert invoked_tools == [METRIC_TOOL_NAME]


async def test_average_states_the_denominator_when_days_are_missing() -> None:
    """The honesty case: a 7-day question answered from 2 days must say so."""
    rows = [_row(date(2026, 5, 14)), _row(date(2026, 5, 15))]
    tool, _reader, _invoked = _build(rows)

    result = await _invoke(tool, metric=DogMetric.TOTAL_SLEEP, days=7)

    assert "only 2 of the 7 days had data" in result


async def test_average_of_a_vital_ignores_days_without_a_reading() -> None:
    rows = [
        _row(date(2026, 5, 14), resting_heart_rate_bpm=70.0),
        _row(date(2026, 5, 15), resting_heart_rate_bpm=None),
    ]
    tool, _reader, _invoked = _build(rows)

    result = await _invoke(tool, metric=DogMetric.RESTING_HEART_RATE, days=2)

    assert "70 bpm" in result
    assert "only 1 of the 2 days had data" in result


async def test_average_reports_no_data_rather_than_zero() -> None:
    tool, _reader, _invoked = _build([])

    result = await _invoke(tool, metric=DogMetric.TOTAL_SLEEP, days=7)

    assert result == "No total sleep is recorded for this dog in the last 7 days."


async def test_on_date_renders_that_days_value() -> None:
    tool, _reader, _invoked = _build([_row(date(2026, 5, 22), total_sleep_hours=11.16)])

    result = await _invoke(
        tool,
        metric=DogMetric.TOTAL_SLEEP,
        aggregation=MetricAggregation.ON_DATE,
        date="2026-05-22",
    )

    assert "Total sleep on 2026-05-22: 11h 10m" in result


async def test_on_date_reports_readings_behind_a_vital() -> None:
    tool, _reader, _invoked = _build([_row(date(2026, 5, 22))])

    result = await _invoke(
        tool,
        metric=DogMetric.RESTING_HEART_RATE,
        aggregation=MetricAggregation.ON_DATE,
        date="2026-05-22",
    )

    assert "68 bpm" in result
    assert "from 12 readings" in result
    assert "give or take 3 bpm" in result


async def test_on_date_without_a_date_asks_for_one_without_querying() -> None:
    tool, reader, _invoked = _build([_row(date(2026, 5, 22))])

    result = await _invoke(
        tool, metric=DogMetric.TOTAL_SLEEP, aggregation=MetricAggregation.ON_DATE
    )

    assert "needs a date" in result
    assert "YYYY-MM-DD" in result
    assert reader.requested_dates == []


async def test_on_date_rejects_a_malformed_date_without_querying() -> None:
    tool, reader, _invoked = _build([_row(date(2026, 5, 22))])

    result = await _invoke(
        tool,
        metric=DogMetric.TOTAL_SLEEP,
        aggregation=MetricAggregation.ON_DATE,
        date="22nd May",
    )

    assert "not a valid date" in result
    assert reader.requested_dates == []


async def test_on_date_reports_no_data_for_a_day_without_a_rollup() -> None:
    tool, _reader, _invoked = _build([_row(date(2026, 5, 22))])

    result = await _invoke(
        tool,
        metric=DogMetric.TOTAL_SLEEP,
        aggregation=MetricAggregation.ON_DATE,
        date="2026-05-23",
    )

    assert result == "No total sleep is recorded for this dog on 2026-05-23."


async def test_daily_series_lists_every_covered_day() -> None:
    rows = [
        _row(date(2026, 5, 14), total_sleep_hours=8.0),
        _row(date(2026, 5, 15), total_sleep_hours=9.0),
    ]
    tool, _reader, _invoked = _build(rows)

    result = await _invoke(
        tool,
        metric=DogMetric.TOTAL_SLEEP,
        aggregation=MetricAggregation.DAILY_SERIES,
        days=2,
    )

    assert "- 2026-05-14: 8h 00m" in result
    assert "- 2026-05-15: 9h 00m" in result


async def test_highest_day_names_the_date_and_value() -> None:
    rows = [
        _row(date(2026, 5, 14), walking_distance_km=2.0),
        _row(date(2026, 5, 15), walking_distance_km=7.5),
    ]
    tool, _reader, _invoked = _build(rows)

    result = await _invoke(
        tool,
        metric=DogMetric.WALKING_DISTANCE,
        aggregation=MetricAggregation.HIGHEST_DAY,
        days=2,
    )

    assert "on 2026-05-15" in result
    assert "7.50 km" in result


async def test_lowest_day_names_the_date_and_value() -> None:
    rows = [
        _row(date(2026, 5, 14), total_sleep_hours=5.0),
        _row(date(2026, 5, 15), total_sleep_hours=9.0),
    ]
    tool, _reader, _invoked = _build(rows)

    result = await _invoke(
        tool,
        metric=DogMetric.TOTAL_SLEEP,
        aggregation=MetricAggregation.LOWEST_DAY,
        days=2,
    )

    assert "on 2026-05-14" in result
    assert "5h 00m" in result


async def test_extreme_over_a_single_day_returns_that_day() -> None:
    tool, _reader, _invoked = _build([_row(date(2026, 5, 14), total_sleep_hours=6.0)])

    result = await _invoke(
        tool,
        metric=DogMetric.TOTAL_SLEEP,
        aggregation=MetricAggregation.HIGHEST_DAY,
        days=1,
    )

    assert "on 2026-05-14" in result
    assert "6h 00m" in result


async def test_extreme_with_tied_values_picks_the_earlier_day() -> None:
    """Ties resolve deterministically, so the same question gives the same answer."""
    rows = [
        _row(date(2026, 5, 14), total_sleep_hours=8.0),
        _row(date(2026, 5, 15), total_sleep_hours=8.0),
    ]
    tool, _reader, _invoked = _build(rows)

    result = await _invoke(
        tool,
        metric=DogMetric.TOTAL_SLEEP,
        aggregation=MetricAggregation.HIGHEST_DAY,
        days=2,
    )

    assert "on 2026-05-14" in result


async def test_every_metric_and_aggregation_pair_renders_without_error() -> None:
    """The registry is a combinatorial surface; walk all of it once."""
    rows = [_row(date(2026, 5, 14)), _row(date(2026, 5, 15))]
    tool, _reader, _invoked = _build(rows)
    for metric in DogMetric:
        for aggregation in MetricAggregation:
            result = await _invoke(
                tool,
                metric=metric,
                aggregation=aggregation,
                days=2,
                date="2026-05-14",
            )
            assert result.strip()


# --------------------------------------------------------------------------- #
# Window clamping
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(0, 1), (-5, 1), (14, 14), (10_000, MAX_WINDOW_DAYS)],
)
def test_clamp_days_keeps_the_window_sane(requested: int, expected: int) -> None:
    assert clamp_days(requested) == expected


async def test_default_window_is_the_default_days() -> None:
    tool, reader, _invoked = _build([_row(date(2026, 5, 14))])
    await _invoke(tool, metric=DogMetric.TOTAL_SLEEP)
    assert reader.requested_days == [DEFAULT_WINDOW_DAYS]


async def test_days_above_max_clamps_down_to_max() -> None:
    tool, reader, _invoked = _build([_row(date(2026, 5, 14))])
    await _invoke(tool, metric=DogMetric.TOTAL_SLEEP, days=10_000)
    assert reader.requested_days == [MAX_WINDOW_DAYS]


@pytest.mark.parametrize("value", ["2026-05-22", " 2026-05-22 "])
def test_parse_iso_date_accepts_iso_with_surrounding_space(value: str) -> None:
    assert parse_iso_date(value) == date(2026, 5, 22)


@pytest.mark.parametrize("value", ["22nd May", "", "2026-13-01"])
def test_parse_iso_date_rejects_anything_else(value: str) -> None:
    assert parse_iso_date(value) is None


# --------------------------------------------------------------------------- #
# Snapshot
# --------------------------------------------------------------------------- #


async def test_snapshot_lists_every_metric() -> None:
    tool, invoked_tools = _build_snapshot([_row(date(2026, 5, 14)), _row(date(2026, 5, 15))])

    result = await _invoke(tool, days=2)

    for spec in METRIC_SPECS.values():
        assert spec.label in result
    assert invoked_tools == [SNAPSHOT_TOOL_NAME]


async def test_snapshot_marks_metrics_with_no_readings_as_no_data() -> None:
    rows = [_row(date(2026, 5, 14), resting_heart_rate_bpm=None)]
    tool, _invoked = _build_snapshot(rows)

    result = await _invoke(tool, days=1)

    assert "resting heart rate: no data" in result


async def test_snapshot_reports_no_data_when_the_window_is_empty() -> None:
    tool, _invoked = _build_snapshot([])

    result = await _invoke(tool, days=7)

    assert result == "No tracker data is recorded for this dog in the last 7 days."


async def test_snapshot_carries_the_floor_caveat() -> None:
    tool, _invoked = _build_snapshot([_row(date(2026, 5, 14))])

    result = await _invoke(tool, days=1)

    assert "floor" in result
    assert "never clinical sleep stages" in result


# --------------------------------------------------------------------------- #
# Tool shape
# --------------------------------------------------------------------------- #


def test_build_returns_both_named_tools() -> None:
    tools = build_pet_data_tools(FakePetDataReader([]), [])
    assert [tool.name for tool in tools] == [METRIC_TOOL_NAME, SNAPSHOT_TOOL_NAME]
    assert all(isinstance(tool, BaseTool) for tool in tools)


def test_tools_have_non_empty_descriptions() -> None:
    tools = build_pet_data_tools(FakePetDataReader([]), [])
    assert all(tool.description.strip() for tool in tools)


def test_metric_tool_description_names_every_metric() -> None:
    """The model picks from this list, so it has to be complete."""
    tools = build_pet_data_tools(FakePetDataReader([]), [])
    for metric in DogMetric:
        assert metric.value in tools[0].description


def test_tools_are_async_only() -> None:
    """The tools read the DB, so they expose a coroutine but no sync func."""
    tools = build_pet_data_tools(FakePetDataReader([]), [])
    for tool in tools:
        assert isinstance(tool, StructuredTool)
        assert tool.coroutine is not None
        assert tool.func is None


# --------------------------------------------------------------------------- #
# The path a real model actually takes: JSON arguments through the tool schema
# --------------------------------------------------------------------------- #


def _args_schema(tool: BaseTool) -> dict[str, Any]:
    """Return a tool's JSON argument schema, narrowing the union LangChain declares."""
    schema = tool.args_schema
    assert isinstance(schema, type) and issubclass(schema, BaseModel)
    return schema.model_json_schema()


def test_schema_constrains_metric_to_the_registry() -> None:
    """The model picks the metric from the schema, so every value must be offered."""
    tools = build_pet_data_tools(FakePetDataReader([]), [])
    definitions = _args_schema(tools[0])["$defs"]
    assert set(definitions["DogMetric"]["enum"]) == {metric.value for metric in DogMetric}
    assert set(definitions["MetricAggregation"]["enum"]) == {
        aggregation.value for aggregation in MetricAggregation
    }


def test_only_metric_is_required() -> None:
    """Everything else has a sensible default, so a one-argument call works."""
    tools = build_pet_data_tools(FakePetDataReader([]), [])
    assert _args_schema(tools[0])["required"] == ["metric"]


async def test_string_arguments_coerce_to_the_enums() -> None:
    """A model sends JSON strings, not enum members."""
    tools = build_pet_data_tools(FakePetDataReader([_row(date(2026, 5, 14))]), [])

    result = await tools[0].ainvoke(
        {"metric": "resting_heart_rate", "aggregation": "on_date", "date": "2026-05-14"}
    )

    assert "68 bpm" in result


async def test_a_metric_outside_the_registry_is_rejected() -> None:
    """The tracker measures no blood values; the schema must not let one through."""
    tools = build_pet_data_tools(FakePetDataReader([_row(date(2026, 5, 14))]), [])

    with pytest.raises(ValidationError):
        await tools[0].ainvoke({"metric": "blood_glucose"})

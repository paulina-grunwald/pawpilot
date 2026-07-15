"""Tests for the dog-data tool built by `build_pet_data_tools`.

Everything here runs against a `FakeSleepReader`, so the tool's rendering, day
clamping, and invocation logging are verified with no database and no network.
"""

from __future__ import annotations

from datetime import date

from langchain_core.tools import BaseTool, StructuredTool

from app.agent.data_tools import (
    DEFAULT_SLEEP_DAYS,
    MAX_SLEEP_DAYS,
    build_pet_data_tools,
)
from app.agent.fakes import FakeSleepReader
from app.integrations.tractive.read_service import DailySleep, SleepSummary

_TOOL_NAME = "get_dog_sleep_summary"
_ON_DATE_TOOL_NAME = "get_dog_sleep_on_date"


def _summary(**overrides: object) -> SleepSummary:
    """A `SleepSummary` with three covered days, overridable per test."""
    values: dict[str, object] = {
        "days_requested": 7,
        "days_with_data": 3,
        "average_total_sleep_hours": 8.0,
        "average_night_sleep_hours": 6.5,
        "average_day_sleep_hours": 1.5,
        "start_date": date(2024, 5, 14),
        "end_date": date(2024, 5, 16),
    }
    values.update(overrides)
    return SleepSummary.model_validate(values)


def _empty_summary(days_requested: int = 7) -> SleepSummary:
    return SleepSummary(
        days_requested=days_requested,
        days_with_data=0,
        average_total_sleep_hours=None,
        average_night_sleep_hours=None,
        average_day_sleep_hours=None,
        start_date=None,
        end_date=None,
    )


def _daily(**overrides: object) -> DailySleep:
    """A `DailySleep` with data present, overridable per test."""
    values: dict[str, object] = {
        "date": date(2024, 5, 22),
        "has_data": True,
        "night_sleep_hours": 6.5,
        "day_sleep_hours": 1.5,
        "total_sleep_hours": 8.0,
    }
    values.update(overrides)
    return DailySleep.model_validate(values)


def _build(summary: SleepSummary) -> tuple[StructuredTool, FakeSleepReader, list[str]]:
    reader = FakeSleepReader(summary)
    invoked_tools: list[str] = []
    tools = build_pet_data_tools(reader, invoked_tools)
    tool = tools[0]
    assert isinstance(tool, StructuredTool)
    return tool, reader, invoked_tools


def _build_on_date(
    reader: FakeSleepReader,
) -> tuple[StructuredTool, list[str]]:
    invoked_tools: list[str] = []
    tools = build_pet_data_tools(reader, invoked_tools)
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
# Tool shape
# --------------------------------------------------------------------------- #


def test_build_returns_both_named_tools() -> None:
    tools = build_pet_data_tools(FakeSleepReader(_summary()), [])
    assert [tool.name for tool in tools] == [_TOOL_NAME, _ON_DATE_TOOL_NAME]
    assert all(isinstance(tool, BaseTool) for tool in tools)


def test_tools_have_non_empty_descriptions() -> None:
    tools = build_pet_data_tools(FakeSleepReader(_summary()), [])
    assert all(tool.description.strip() for tool in tools)


def test_tools_are_async_only() -> None:
    """The tools read the DB, so they expose a coroutine but no sync func."""
    tools = build_pet_data_tools(FakeSleepReader(_summary()), [])
    for tool in tools:
        assert isinstance(tool, StructuredTool)
        assert tool.coroutine is not None
        assert tool.func is None


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


async def test_renders_averages_and_coverage_when_data_present() -> None:
    tool, _reader, invoked_tools = _build(_summary())

    result = await _invoke(tool, days=7)

    assert "data for 3 of them" in result
    assert "2024-05-14 to 2024-05-16" in result
    assert "Average total sleep: 8.0 hours/day" in result
    assert "Average night sleep: 6.5 hours/day" in result
    assert "Average daytime sleep: 1.5 hours/day" in result
    assert invoked_tools == [_TOOL_NAME]


async def test_renders_no_data_message_when_window_is_empty() -> None:
    tool, _reader, invoked_tools = _build(_empty_summary(days_requested=7))

    result = await _invoke(tool, days=7)

    assert result == "No tracker sleep data is recorded for this dog in the last 7 days."
    assert invoked_tools == [_TOOL_NAME]


# --------------------------------------------------------------------------- #
# Day window
# --------------------------------------------------------------------------- #


async def test_default_window_is_the_default_days() -> None:
    tool, reader, _invoked = _build(_summary())
    await _invoke(tool)
    assert reader.requested_days == [DEFAULT_SLEEP_DAYS]


async def test_days_below_one_clamps_up_to_one() -> None:
    tool, reader, _invoked = _build(_summary())
    await _invoke(tool, days=0)
    assert reader.requested_days == [1]


async def test_days_above_max_clamps_down_to_max() -> None:
    tool, reader, _invoked = _build(_summary())
    await _invoke(tool, days=1000)
    assert reader.requested_days == [MAX_SLEEP_DAYS]


async def test_days_within_range_passes_through_unchanged() -> None:
    tool, reader, _invoked = _build(_summary())
    await _invoke(tool, days=14)
    assert reader.requested_days == [14]


# --------------------------------------------------------------------------- #
# get_dog_sleep_on_date
# --------------------------------------------------------------------------- #


async def test_on_date_renders_that_days_sleep_when_data_present() -> None:
    reader = FakeSleepReader(_summary(), daily=_daily())
    tool, invoked_tools = _build_on_date(reader)

    result = await _invoke(tool, date="2024-05-22")

    assert "Sleep on 2024-05-22:" in result
    assert "Total sleep: 8.0 hours" in result
    assert "Night sleep: 6.5 hours" in result
    assert "Daytime sleep: 1.5 hours" in result
    assert invoked_tools == [_ON_DATE_TOOL_NAME]


async def test_on_date_parses_and_forwards_the_requested_date() -> None:
    reader = FakeSleepReader(_summary(), daily=_daily())
    tool, _invoked = _build_on_date(reader)

    await _invoke(tool, date=" 2024-05-22 ")

    assert reader.requested_dates == [date(2024, 5, 22)]


async def test_on_date_renders_no_data_message_when_day_has_no_rollup() -> None:
    reader = FakeSleepReader(_summary())  # no daily -> reader reports no data
    tool, invoked_tools = _build_on_date(reader)

    result = await _invoke(tool, date="2024-05-22")

    assert result == "No tracker sleep data is recorded for this dog on 2024-05-22."
    assert invoked_tools == [_ON_DATE_TOOL_NAME]


async def test_on_date_rejects_a_malformed_date_without_querying() -> None:
    reader = FakeSleepReader(_summary(), daily=_daily())
    tool, invoked_tools = _build_on_date(reader)

    result = await _invoke(tool, date="22nd May")

    assert "not a valid date" in result
    assert "YYYY-MM-DD" in result
    assert reader.requested_dates == []  # never reached the reader
    assert invoked_tools == [_ON_DATE_TOOL_NAME]

"""Tests for the clock tool built by `build_datetime_tools`.

The clock is injected, so rendering and invocation logging are verified against a
fixed instant with no reliance on the wall clock. Two weekdays are pinned by hand
(2024-05-22 is a Wednesday, 2026-01-01 is a Thursday) so the assertions do not
just echo `strftime` back to itself.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from langchain_core.tools import BaseTool, StructuredTool

from app.agent.datetime_tools import (
    CURRENT_DATE_TOOL_NAME,
    Clock,
    _utc_now,
    build_datetime_tools,
    render_current_date,
)


def _fixed_clock(moment: datetime) -> Clock:
    """A clock that always returns ``moment``."""
    return lambda: moment


def _build(moment: datetime) -> tuple[StructuredTool, list[str]]:
    invoked_tools: list[str] = []
    tools = build_datetime_tools(invoked_tools, clock=_fixed_clock(moment))
    tool = tools[0]
    assert isinstance(tool, StructuredTool)
    return tool, invoked_tools


# --------------------------------------------------------------------------- #
# Tool shape
# --------------------------------------------------------------------------- #


def test_build_returns_the_named_clock_tool() -> None:
    tools = build_datetime_tools([])
    assert [tool.name for tool in tools] == [CURRENT_DATE_TOOL_NAME]
    assert all(isinstance(tool, BaseTool) for tool in tools)


def test_tool_has_non_empty_description() -> None:
    tool = build_datetime_tools([])[0]
    assert tool.description.strip()


def test_tool_is_sync_and_takes_no_query() -> None:
    """The tool does no IO, so it exposes a sync func usable in both run paths."""
    tool = build_datetime_tools([])[0]
    assert isinstance(tool, StructuredTool)
    assert tool.func is not None


# --------------------------------------------------------------------------- #
# render_current_date (pure)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (
            datetime(2024, 5, 22, 13, 30, tzinfo=UTC),
            "Today's date is 2024-05-22 (Wednesday, UTC).",
        ),
        (
            datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
            "Today's date is 2026-01-01 (Thursday, UTC).",
        ),
    ],
)
def test_render_leads_with_iso_date_and_names_the_weekday(moment: datetime, expected: str) -> None:
    assert render_current_date(moment) == expected


def test_render_uses_the_datetimes_own_date_not_a_conversion() -> None:
    # Just before midnight UTC still renders that same calendar day.
    moment = datetime(2026, 7, 14, 23, 59, tzinfo=UTC)
    assert render_current_date(moment) == "Today's date is 2026-07-14 (Tuesday, UTC)."


# --------------------------------------------------------------------------- #
# Invocation
# --------------------------------------------------------------------------- #


def test_tool_returns_rendered_date_for_the_injected_clock() -> None:
    tool, _invoked = _build(datetime(2026, 7, 15, 9, 0, tzinfo=UTC))
    assert tool.func is not None

    result = tool.func()

    assert result == "Today's date is 2026-07-15 (Wednesday, UTC)."


def test_tool_records_each_invocation() -> None:
    tool, invoked_tools = _build(datetime(2026, 7, 15, tzinfo=UTC))
    assert tool.func is not None

    tool.func()
    tool.func()

    assert invoked_tools == [CURRENT_DATE_TOOL_NAME, CURRENT_DATE_TOOL_NAME]


def test_tool_invokes_through_the_langchain_interface() -> None:
    tool, invoked_tools = _build(datetime(2026, 1, 1, tzinfo=UTC))

    result = tool.invoke({})

    assert result == "Today's date is 2026-01-01 (Thursday, UTC)."
    assert invoked_tools == [CURRENT_DATE_TOOL_NAME]


# --------------------------------------------------------------------------- #
# Default clock
# --------------------------------------------------------------------------- #


def test_default_clock_returns_timezone_aware_utc() -> None:
    now = _utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo == UTC


def test_default_clock_output_matches_the_render_format() -> None:
    tool = build_datetime_tools([])[0]
    assert isinstance(tool, StructuredTool)
    assert tool.func is not None

    result = tool.func()

    assert result == render_current_date(_utc_now())

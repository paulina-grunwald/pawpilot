"""A small clock tool: lets the model find out what today's date is.

The model resolves relative or year-less dates itself ("yesterday", "14 July"),
but only if it knows what today is. Without this it has to guess the year, which
is how a question about "the 14th" can silently land on the wrong day. This tool
hands the model today's date so those resolutions are grounded.

The clock is injected so the tool is deterministic under test. Production uses the
current instant in UTC, matching how the dashboard renders stored rollup dates.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from langchain_core.tools import BaseTool, StructuredTool

Clock = Callable[[], datetime]

CURRENT_DATE_TOOL_NAME = "get_current_date"
_CURRENT_DATE_TOOL_DESCRIPTION = (
    "Get today's date. Use it whenever a correct answer depends on knowing today: "
    "to resolve a date the owner gives without a year, for example '14 July', or a "
    "relative day, for example 'yesterday', 'last Tuesday', or 'this week'. Takes "
    "no arguments and returns today's date as ISO YYYY-MM-DD with its weekday, in "
    "UTC."
)


def _utc_now() -> datetime:
    """Default clock: the current instant, timezone-aware in UTC."""
    return datetime.now(UTC)


def render_current_date(moment: datetime) -> str:
    """Render an instant as the plain text the model reads back.

    Leads with the ISO date so the model can lift it straight into
    get_dog_sleep_on_date, and names the weekday so relative days resolve.
    """
    return f"Today's date is {moment.date().isoformat()} ({moment.strftime('%A')}, UTC)."


def build_datetime_tools(invoked_tools: list[str], clock: Clock = _utc_now) -> list[BaseTool]:
    """Build the always-on clock tool, appending each call to ``invoked_tools``."""

    def get_current_date() -> str:
        invoked_tools.append(CURRENT_DATE_TOOL_NAME)
        return render_current_date(clock())

    return [
        StructuredTool.from_function(
            func=get_current_date,
            name=CURRENT_DATE_TOOL_NAME,
            description=_CURRENT_DATE_TOOL_DESCRIPTION,
        )
    ]

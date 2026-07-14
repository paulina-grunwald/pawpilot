"""The dog-data tool: reads this dog's own tracker sleep from the database.

Bound per run to a `SleepDataReader` that is already scoped to the owner's pet,
so the model chooses only the time window, never whose data it reads. The tool is
async-only because the reader is a database query and a DB-backed run is always
driven by ``ainvoke``.
"""

from __future__ import annotations

from typing import Protocol

from langchain_core.tools import BaseTool, StructuredTool

from app.integrations.tractive.read_service import SleepSummary

DEFAULT_SLEEP_DAYS = 7
MAX_SLEEP_DAYS = 90

_TOOL_NAME = "get_dog_sleep_summary"
_TOOL_DESCRIPTION = (
    "Look up how much THIS dog actually slept, from its activity tracker. Use it "
    "for questions about the dog's own measured sleep or rest, for example 'how "
    "many hours did my dog sleep this week?'. Pass the number of days to look back "
    f"(default {DEFAULT_SLEEP_DAYS}, at most {MAX_SLEEP_DAYS}). Returns the average "
    "night, daytime, and total sleep per day, and how many of those days had data."
)


class SleepDataReader(Protocol):
    """Reads averaged sleep for one already-scoped dog over a day window."""

    async def summarize_sleep(self, days: int) -> SleepSummary: ...


def build_pet_data_tools(reader: SleepDataReader, invoked_tools: list[str]) -> list[BaseTool]:
    """Build the dog-data tools bound to one run's owner-scoped ``reader``."""

    async def get_dog_sleep_summary(days: int = DEFAULT_SLEEP_DAYS) -> str:
        invoked_tools.append(_TOOL_NAME)
        summary = await reader.summarize_sleep(_clamp_days(days))
        return _render_sleep_summary(summary)

    return [
        StructuredTool.from_function(
            coroutine=get_dog_sleep_summary,
            name=_TOOL_NAME,
            description=_TOOL_DESCRIPTION,
        )
    ]


def _clamp_days(days: int) -> int:
    """Keep the look-back window within a sane range whatever the model asks for."""
    return max(1, min(days, MAX_SLEEP_DAYS))


def _render_sleep_summary(summary: SleepSummary) -> str:
    """Render a `SleepSummary` as the plain text the model reads back."""
    if summary.days_with_data == 0:
        return (
            "No tracker sleep data is recorded for this dog in the last "
            f"{summary.days_requested} days."
        )
    return (
        f"Sleep over the last {summary.days_requested} days "
        f"(data for {summary.days_with_data} of them, {summary.start_date} to "
        f"{summary.end_date}):\n"
        f"- Average total sleep: {summary.average_total_sleep_hours} hours/day\n"
        f"- Average night sleep: {summary.average_night_sleep_hours} hours/day\n"
        f"- Average daytime sleep: {summary.average_day_sleep_hours} hours/day"
    )

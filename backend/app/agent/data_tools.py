"""The dog-data tools: read this dog's own tracker sleep from the database.

Bound per run to a `SleepDataReader` that is already scoped to the owner's pet,
so the model chooses only the time window or date, never whose data it reads. The
tools are async-only because the reader is a database query and a DB-backed run is
always driven by ainvoke.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Protocol

from langchain_core.tools import BaseTool, StructuredTool

from app.integrations.tractive.read_service import DailySleep, SleepSummary

DEFAULT_SLEEP_DAYS = 7
MAX_SLEEP_DAYS = 90

_SUMMARY_TOOL_NAME = "get_dog_sleep_summary"
_SUMMARY_TOOL_DESCRIPTION = (
    "Look up how much THIS dog actually slept, from its activity tracker. Use it "
    "for questions about the dog's own measured sleep or rest over a recent window, "
    "for example 'how many hours did my dog sleep this week?'. Pass the number of "
    f"days to look back (default {DEFAULT_SLEEP_DAYS}, at most {MAX_SLEEP_DAYS}). "
    "Returns the average night, daytime, and total sleep per day, and how many of "
    "those days had data."
)

_ON_DATE_TOOL_NAME = "get_dog_sleep_on_date"
_ON_DATE_TOOL_DESCRIPTION = (
    "Look up how much THIS dog slept on one specific calendar day, from its "
    "activity tracker. Use it when the owner asks about a named date, for example "
    "'how many hours did my dog sleep on 22 May?'. Pass the date in ISO format "
    "YYYY-MM-DD. Returns that day's night, daytime, and total sleep, or says so "
    "when no data was recorded for that day."
)


class SleepDataReader(Protocol):
    """Reads one already-scoped dog's sleep: averaged over a window, or one day."""

    async def summarize_sleep(self, days: int) -> SleepSummary: ...

    async def sleep_on_date(self, day: date_type) -> DailySleep: ...


def build_pet_data_tools(reader: SleepDataReader, invoked_tools: list[str]) -> list[BaseTool]:
    """Build the dog-data tools bound to one run's owner-scoped ``reader``."""

    async def get_dog_sleep_summary(days: int = DEFAULT_SLEEP_DAYS) -> str:
        invoked_tools.append(_SUMMARY_TOOL_NAME)
        summary = await reader.summarize_sleep(_clamp_days(days))
        return _render_sleep_summary(summary)

    async def get_dog_sleep_on_date(date: str) -> str:
        invoked_tools.append(_ON_DATE_TOOL_NAME)
        day = _parse_iso_date(date)
        if day is None:
            return f"'{date}' is not a valid date. Provide the date in ISO format YYYY-MM-DD."
        return _render_daily_sleep(await reader.sleep_on_date(day))

    return [
        StructuredTool.from_function(
            coroutine=get_dog_sleep_summary,
            name=_SUMMARY_TOOL_NAME,
            description=_SUMMARY_TOOL_DESCRIPTION,
        ),
        StructuredTool.from_function(
            coroutine=get_dog_sleep_on_date,
            name=_ON_DATE_TOOL_NAME,
            description=_ON_DATE_TOOL_DESCRIPTION,
        ),
    ]


def _clamp_days(days: int) -> int:
    """Keep the look-back window within a sane range whatever the model asks for."""
    return max(1, min(days, MAX_SLEEP_DAYS))


def _parse_iso_date(value: str) -> date_type | None:
    """Parse an ISO ``YYYY-MM-DD`` string, or None when the model sent something else."""
    try:
        return date_type.fromisoformat(value.strip())
    except ValueError:
        return None


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


def _render_daily_sleep(daily: DailySleep) -> str:
    """Render a `DailySleep` as the plain text the model reads back."""
    if not daily.has_data:
        return f"No tracker sleep data is recorded for this dog on {daily.date}."
    return (
        f"Sleep on {daily.date}:\n"
        f"- Total sleep: {daily.total_sleep_hours} hours\n"
        f"- Night sleep: {daily.night_sleep_hours} hours\n"
        f"- Daytime sleep: {daily.day_sleep_hours} hours"
    )

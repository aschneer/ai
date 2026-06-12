"""Working-day calendar math for schedule duration and lag calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from schedule.predecessors_lib import parse_duration_to_working_days

WEEKDAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@dataclass(frozen=True)
class WorkingCalendar:
    """Weekends and holidays that exclude days from working-day arithmetic."""

    weekends: frozenset[int]
    holidays: frozenset[date]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkingCalendar:
        """Build a calendar from parsed ``calendar.yaml`` data."""
        weekends = {WEEKDAY_NAMES.index(day) for day in data.get("weekends", ["sat", "sun"])}
        holidays = {date.fromisoformat(day) for day in data.get("holidays", [])}
        return cls(weekends=frozenset(weekends), holidays=frozenset(holidays))

    def is_working_day(self, day: date) -> bool:
        """Return True when work may occur on ``day``."""
        return day.weekday() not in self.weekends and day not in self.holidays

    def normalize_to_working_day(self, day: date, direction: int = 1) -> date:
        """Move forward (or backward) to the nearest working day."""
        current = day
        while not self.is_working_day(current):
            current += timedelta(days=direction)
        return current

    def add_working_days(self, start: date, working_days: int) -> date:
        """Add signed working days to ``start``, skipping non-working days."""
        if working_days == 0:
            return self.normalize_to_working_day(start)
        current = self.normalize_to_working_day(start)
        remaining = abs(working_days)
        step = 1 if working_days > 0 else -1
        while remaining > 0:
            current += timedelta(days=step)
            if self.is_working_day(current):
                remaining -= 1
        return current

    def task_finish(self, start: date, duration: str) -> date:
        """Compute finish date for a task starting on ``start`` with ``duration``."""
        working_days = parse_duration_to_working_days(duration)
        if working_days <= 0:
            return start
        return self.add_working_days(start, working_days - 1)

    def apply_lag(self, anchor: date, lag: str | None) -> date:
        """Shift ``anchor`` by optional lag/lead (``+3d``, ``-1w``)."""
        if not lag:
            return anchor
        offset = parse_duration_to_working_days(lag)
        return self.add_working_days(anchor, offset)

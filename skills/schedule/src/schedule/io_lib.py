"""Load schedule and calendar YAML with JSON-Schema-friendly normalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from schedule.validate_lib import validate_calendar_file, validate_schedule_file


@dataclass(frozen=True)
class ScheduleProject:
    """Loaded and validated schedule and calendar files from one project directory."""

    schedule_path: Path
    schedule_data: dict[str, Any]
    calendar_path: Path
    calendar_data: dict[str, Any] | None


def load_yaml(path: Path) -> Any:
    """Load YAML from disk and normalize dates for schema validation."""
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return normalize_for_schema(data)


def normalize_for_schema(data: Any) -> Any:
    """Convert ``datetime.date`` values to ISO strings for JSON Schema."""
    if isinstance(data, dict):
        return {key: normalize_for_schema(value) for key, value in data.items()}
    if isinstance(data, list):
        return [normalize_for_schema(value) for value in data]
    if isinstance(data, datetime):
        return data.date().isoformat()
    if isinstance(data, date):
        return data.isoformat()
    return data


def calendar_path_for_schedule(schedule_path: Path, schedule_data: dict[str, Any]) -> Path:
    """Resolve the calendar file path relative to the schedule file location."""
    calendar_ref = schedule_data.get("calendar", "calendar.yaml")
    return (schedule_path.parent / calendar_ref).resolve()


def load_schedule_project(
    schedule_path: Path,
    *,
    require_calendar: bool,
) -> tuple[ScheduleProject | None, list[str]]:
    """Load schedule YAML, optionally load calendar, and validate both against schema."""
    schedule_path = schedule_path.resolve()
    errors: list[str] = []

    if not schedule_path.is_file():
        return None, [f"error: schedule file not found: {schedule_path}"]

    try:
        schedule_data = load_yaml(schedule_path)
    except yaml.YAMLError as exc:
        return None, [f"error: invalid YAML in {schedule_path}: {exc}"]

    if not isinstance(schedule_data, dict):
        return None, [
            f"error: schedule file must be a mapping with an items list: {schedule_path}"
        ]

    errors.extend(validate_schedule_file(schedule_path, schedule_data))
    calendar_path = calendar_path_for_schedule(schedule_path, schedule_data)
    calendar_data: dict[str, Any] | None = None

    if calendar_path.is_file():
        try:
            calendar_data = load_yaml(calendar_path)
        except yaml.YAMLError as exc:
            errors.append(f"error: invalid YAML in {calendar_path}: {exc}")
        else:
            if not isinstance(calendar_data, dict):
                errors.append(f"error: calendar file must be a mapping: {calendar_path}")
            else:
                errors.extend(validate_calendar_file(calendar_path, calendar_data))
    elif require_calendar or schedule_data.get("calendar"):
        errors.append(f"calendar: referenced file not found: {calendar_path}")

    if errors:
        return None, errors

    return (
        ScheduleProject(
            schedule_path=schedule_path,
            schedule_data=schedule_data,
            calendar_path=calendar_path,
            calendar_data=calendar_data,
        ),
        [],
    )


"""Validate schedule and calendar YAML against JSON Schema.

Usage (from skills/schedule/):
    uv sync
    uv run schedule-validate <schedule-file>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from schedule.io_lib import calendar_path_for_schedule, load_yaml
from schedule.validate_lib import validate_calendar_file, validate_schedule_file


def main(argv: list[str] | None = None) -> int:
    """Validate schedule and optional calendar; print ok or errors to stderr."""
    parser = argparse.ArgumentParser(description="Validate schedule and calendar YAML files.")
    parser.add_argument("schedule_file", type=Path, help="Path to schedule YAML file")
    args = parser.parse_args(argv)

    schedule_path = args.schedule_file.resolve()
    if not schedule_path.is_file():
        print(f"error: schedule file not found: {schedule_path}", file=sys.stderr)
        return 1

    try:
        schedule_data = load_yaml(schedule_path)
    except yaml.YAMLError as exc:
        print(f"error: invalid YAML in {schedule_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(schedule_data, dict):
        print(f"error: schedule file must be a mapping with an items list: {schedule_path}", file=sys.stderr)
        return 1

    errors = validate_schedule_file(schedule_path, schedule_data)
    calendar_path = calendar_path_for_schedule(schedule_path, schedule_data)

    if calendar_path.is_file():
        try:
            calendar_data = load_yaml(calendar_path)
        except yaml.YAMLError as exc:
            print(f"error: invalid YAML in {calendar_path}: {exc}", file=sys.stderr)
            return 1
        if not isinstance(calendar_data, dict):
            print(f"error: calendar file must be a mapping: {calendar_path}", file=sys.stderr)
            return 1
        errors.extend(validate_calendar_file(calendar_path, calendar_data))
    elif schedule_data.get("calendar"):
        errors.append(f"calendar: referenced file not found: {calendar_path}")

    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    print(f"ok: {schedule_path.name}")
    if calendar_path.is_file():
        print(f"ok: {calendar_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

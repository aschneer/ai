"""Compute schedule dates (CPM) and print JSON to stdout.

Usage (from skills/schedule/):
    uv run schedule-compute <schedule-file>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from schedule.compute_lib import computed_schedule_to_dict, compute_schedule
from schedule.io_lib import calendar_path_for_schedule, load_yaml
from schedule.validate_lib import validate_calendar_file, validate_schedule_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute schedule dates from YAML (CPM).")
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
    if not calendar_path.is_file():
        print(f"error: calendar file not found: {calendar_path}", file=sys.stderr)
        return 1

    try:
        calendar_data = load_yaml(calendar_path)
    except yaml.YAMLError as exc:
        print(f"error: invalid YAML in {calendar_path}: {exc}", file=sys.stderr)
        return 1

    if not isinstance(calendar_data, dict):
        print(f"error: calendar file must be a mapping: {calendar_path}", file=sys.stderr)
        return 1

    errors.extend(validate_calendar_file(calendar_path, calendar_data))
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    result = compute_schedule(schedule_data, calendar_data)
    print(json.dumps(computed_schedule_to_dict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

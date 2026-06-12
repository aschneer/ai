"""Validate schedule and calendar YAML against JSON Schema.

Usage (from skills/schedule/):
    uv sync
    uv run schedule-validate <schedule-file>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schedule.io_lib import load_schedule_project


def main(argv: list[str] | None = None) -> int:
    """Validate schedule and optional calendar; print ok or errors to stderr."""
    parser = argparse.ArgumentParser(description="Validate schedule and calendar YAML files.")
    parser.add_argument("schedule_file", type=Path, help="Path to schedule YAML file")
    args = parser.parse_args(argv)

    project, errors = load_schedule_project(args.schedule_file, require_calendar=False)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    assert project is not None
    print(f"ok: {project.schedule_path.name}")
    if project.calendar_data is not None:
        print(f"ok: {project.calendar_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

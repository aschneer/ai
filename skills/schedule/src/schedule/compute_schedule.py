"""Compute schedule dates (CPM) and print JSON to stdout.

Usage (from skills/schedule/):
    uv run schedule-compute <schedule-file>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schedule.compute_lib import computed_schedule_to_dict, compute_schedule
from schedule.io_lib import load_schedule_project


def main(argv: list[str] | None = None) -> int:
    """Validate, compute CPM dates, and print JSON to stdout."""
    parser = argparse.ArgumentParser(description="Compute schedule dates from YAML (CPM).")
    parser.add_argument("schedule_file", type=Path, help="Path to schedule YAML file")
    args = parser.parse_args(argv)

    project, errors = load_schedule_project(args.schedule_file, require_calendar=True)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    assert project is not None and project.calendar_data is not None
    result = compute_schedule(project.schedule_data, project.calendar_data)
    print(json.dumps(computed_schedule_to_dict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

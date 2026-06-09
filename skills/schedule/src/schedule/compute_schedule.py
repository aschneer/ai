"""Compute schedule dates (CPM) and print JSON to stdout.

Usage (from skills/schedule/):
    uv run schedule-compute <schedule-file>

Not yet implemented — deterministic CPM calculation will live in schedule *_lib modules.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute schedule dates from YAML (CPM).")
    parser.add_argument("schedule_file", type=Path, help="Path to schedule YAML file")
    args = parser.parse_args(argv)

    if not args.schedule_file.is_file():
        print(f"error: schedule file not found: {args.schedule_file}", file=sys.stderr)
        return 1

    print("error: schedule-compute is not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

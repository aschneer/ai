"""Render a static HTML Gantt chart from a schedule file.

Usage (from skills/schedule/):
    uv run schedule-render <schedule-file> -o gantt.html

Not yet implemented — HTML rendering will live in schedule *_lib modules.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render static HTML Gantt from schedule YAML.")
    parser.add_argument("schedule_file", type=Path, help="Path to schedule YAML file")
    parser.add_argument("-o", "--output", type=Path, default=Path("gantt.html"), help="Output HTML path")
    args = parser.parse_args(argv)

    if not args.schedule_file.is_file():
        print(f"error: schedule file not found: {args.schedule_file}", file=sys.stderr)
        return 1

    print("error: schedule-render is not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

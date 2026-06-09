#!/usr/bin/env python3
"""Render a static HTML Gantt chart from a schedule file.

Usage:
    render_gantt.py <schedule-file> -o gantt.html

Not yet implemented — HTML rendering will live in schedule_lib/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render static HTML Gantt from schedule YAML.")
    parser.add_argument("schedule_file", type=Path, help="Path to schedule YAML file")
    parser.add_argument("-o", "--output", type=Path, default=Path("gantt.html"), help="Output HTML path")
    args = parser.parse_args()

    if not args.schedule_file.is_file():
        print(f"error: schedule file not found: {args.schedule_file}", file=sys.stderr)
        return 1

    print("error: render_gantt.py is not implemented yet", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Render a static HTML Gantt chart from a schedule file.

Usage (from skills/schedule/):
    uv run schedule-render <schedule-file> -o gantt.html
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from schedule.compute_lib import compute_schedule
from schedule.io_lib import load_schedule_project
from schedule.render_gantt_lib import render_gantt_html


def main(argv: list[str] | None = None) -> int:
    """Validate, compute, and write a static HTML Gantt chart."""
    parser = argparse.ArgumentParser(description="Render static HTML Gantt from schedule YAML.")
    parser.add_argument("schedule_file", type=Path, help="Path to schedule YAML file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output HTML path (default: gantt.html beside the schedule file)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Page title (default: schedule file stem)",
    )
    args = parser.parse_args(argv)

    project, errors = load_schedule_project(args.schedule_file, require_calendar=True)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    assert project is not None and project.calendar_data is not None
    result = compute_schedule(project.schedule_data, project.calendar_data)
    title = args.title or project.schedule_path.stem
    output_path = (args.output or project.schedule_path.parent / "gantt.html").resolve()
    html_content = render_gantt_html(result, title=title)
    output_path.write_text(html_content, encoding="utf-8")
    print(f"ok: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

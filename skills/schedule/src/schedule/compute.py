"""Compute schedule dates, write Gantt data, and serve the chart.

Usage (from skills/schedule/):
    uv run compute <schedule-file>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from schedule.compute_lib import computed_schedule_to_dict, compute_schedule
from schedule.gantt_lib import (
    GANTT_DATA_FILENAME,
    SITE_DIR,
    deploy_gantt_assets,
    deploy_project_gitignore,
    deploy_recompute_script,
    schedule_payload,
    serve_project_directory,
    site_directory,
    write_gantt_data,
)
from schedule.io_lib import load_schedule_project


def main(argv: list[str] | None = None) -> int:
    """Validate, compute, write gantt_data.json, deploy viewer, print JSON, and serve."""
    parser = argparse.ArgumentParser(description="Compute schedule and publish Gantt viewer.")
    parser.add_argument("schedule_file", type=Path, help="Path to schedule YAML file")
    parser.add_argument(
        "--data",
        type=Path,
        help=f"JSON output path (default: {SITE_DIR}/{GANTT_DATA_FILENAME} beside the schedule file)",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Schedule title for the Gantt page (default: schedule file stem)",
    )
    parser.add_argument(
        "--stdout",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print JSON to stdout (default: true)",
    )
    parser.add_argument(
        "--serve",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Serve the project site/ directory after compute (default: true)",
    )
    parser.add_argument(
        "--host",
        default="auto",
        help="Bind address: auto (0.0.0.0), 127.0.0.1, or 0.0.0.0 (default: auto)",
    )
    parser.add_argument("--port", type=int, default=8000, help="HTTP port for --serve")
    args = parser.parse_args(argv)

    project, errors = load_schedule_project(args.schedule_file, require_calendar=True)
    if errors:
        for message in errors:
            print(message, file=sys.stderr)
        return 1

    assert project is not None and project.calendar_data is not None
    result = compute_schedule(project.schedule_data, project.calendar_data)
    title = args.title or project.schedule_path.stem
    payload = schedule_payload(computed_schedule_to_dict(result), title=title)

    project_dir = project.schedule_path.parent
    site_dir = site_directory(project_dir)
    data_path = (args.data or site_dir / GANTT_DATA_FILENAME).resolve()
    write_gantt_data(data_path, payload)
    asset_paths = deploy_gantt_assets(site_dir)
    gitignore_path = deploy_project_gitignore(project_dir)
    recompute_path = deploy_recompute_script(project_dir, project.schedule_path.name)

    try:
        data_rel = data_path.relative_to(project_dir.resolve())
    except ValueError:
        data_rel = data_path
    print(f"ok: {data_rel}", file=sys.stderr)
    for path in asset_paths:
        try:
            rel = path.relative_to(project_dir.resolve())
        except ValueError:
            rel = path
        print(f"ok: {rel}", file=sys.stderr)
    if gitignore_path is not None:
        try:
            rel = gitignore_path.relative_to(project_dir.resolve())
        except ValueError:
            rel = gitignore_path
        print(f"ok: {rel}", file=sys.stderr)
    try:
        rel = recompute_path.relative_to(project_dir.resolve())
    except ValueError:
        rel = recompute_path
    print(f"ok: {rel}", file=sys.stderr)

    if args.stdout:
        print(json.dumps(payload, indent=2))

    if args.serve:
        serve_project_directory(project_dir, port=args.port, host=args.host)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

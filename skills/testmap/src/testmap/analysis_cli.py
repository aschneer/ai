"""CLI for the agent to read/write analysis.json one entry at a time (PRD 11).

Usage:
    uv run analysis-cli read      <analysis_json> <symbol_id>
    uv run analysis-cli write     <analysis_json> <symbol_id> <json|->
    uv run analysis-cli list-keys <analysis_json>

``write`` takes the entry JSON as an argument, or ``-`` to read it from stdin (use
stdin for large entries). Cross-file queries (stale, summary, and reads of other
data files) live in the read-only ``query`` CLI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from testmap import analysis_lib


def main(argv: list[str] | None = None) -> int:
    """Dispatch an analysis-cli subcommand."""
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 1

    command, analysis_path = argv[0], Path(argv[1]).resolve()
    handlers = {
        "read": lambda: _read(analysis_path, argv[2:]),
        "write": lambda: _write(analysis_path, argv[2:]),
        "list-keys": lambda: _list_keys(analysis_path),
    }
    handler = handlers.get(command)
    if handler is None:
        print(f"error: unknown command: {command}", file=sys.stderr)
        return 1
    return handler()


def _read(analysis_path: Path, args: list[str]) -> int:
    """Print one symbol's analysis entry as JSON."""
    if len(args) != 1:
        print("usage: read <analysis_json> <symbol_id>", file=sys.stderr)
        return 1
    entry = analysis_lib.read_entry(analysis_path, args[0])
    if entry is None:
        print(f"error: no entry for symbol: {args[0]}", file=sys.stderr)
        return 1
    print(json.dumps(entry, indent=2, sort_keys=True))
    return 0


def _write(analysis_path: Path, args: list[str]) -> int:
    """Validate and upsert one symbol's analysis entry."""
    if len(args) != 2:
        print("usage: write <analysis_json> <symbol_id> <json|->", file=sys.stderr)
        return 1
    symbol_id, raw = args[0], (sys.stdin.read() if args[1] == "-" else args[1])
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON: {exc}", file=sys.stderr)
        return 1
    errors = analysis_lib.write_entry(analysis_path, symbol_id, entry)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"wrote entry: {symbol_id}")
    return 0


def _list_keys(analysis_path: Path) -> int:
    """Print every analyzed symbol key, one per line."""
    for symbol_id in sorted(analysis_lib.load_analysis(analysis_path)):
        print(symbol_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())

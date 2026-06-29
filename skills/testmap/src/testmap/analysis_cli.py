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

import argparse
import json
import sys
from pathlib import Path

from testmap import analysis_lib


def main(argv: list[str] | None = None) -> int:
    """Dispatch an analysis-cli subcommand."""
    parser = argparse.ArgumentParser(description="Read and write analysis.json one entry at a time.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read", help="print one symbol's analysis entry")
    p_read.add_argument("analysis_json")
    p_read.add_argument("symbol_id")

    p_write = sub.add_parser("write", help="validate and upsert one symbol's entry")
    p_write.add_argument("analysis_json")
    p_write.add_argument("symbol_id")
    p_write.add_argument("json", help="the entry JSON, or - to read it from stdin")

    p_keys = sub.add_parser("list-keys", help="print all analyzed symbol keys")
    p_keys.add_argument("analysis_json")

    args = parser.parse_args(argv)
    analysis_path = Path(args.analysis_json).resolve()
    if args.command == "read":
        return _read(analysis_path, args.symbol_id)
    if args.command == "write":
        return _write(analysis_path, args.symbol_id, args.json)
    return _list_keys(analysis_path)


def _read(analysis_path: Path, symbol_id: str) -> int:
    """Print one symbol's analysis entry as JSON."""
    entry = analysis_lib.read_entry(analysis_path, symbol_id)
    if entry is None:
        print(f"error: no entry for symbol: {symbol_id}", file=sys.stderr)
        return 1
    print(json.dumps(entry, indent=2, sort_keys=True))
    return 0


def _write(analysis_path: Path, symbol_id: str, json_arg: str) -> int:
    """Validate and upsert one symbol's analysis entry."""
    raw = sys.stdin.read() if json_arg == "-" else json_arg
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

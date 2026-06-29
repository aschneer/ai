"""Read-only CLI for the agent to query pipeline data files (PRD 11).

Usage:
    uv run query <output_dir> index  <symbol_id>
    uv run query <output_dir> triage <symbol_id>
    uv run query <output_dir> stale
    uv run query <output_dir> summary

Per-file lookups print one symbol's record as JSON. ``stale`` lists symbols that
are stale or unanalyzed (PRD 3.1); ``summary`` prints counts (total, analyzed,
stale, by priority). All commands take the output directory so cross-file queries
resolve every data file from one place. Analysis writes use the ``analysis-cli``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from testmap import analysis_lib, schema_lib, staleness_lib

_PER_FILE = {
    "index": ("index.json", "index"),
    "triage": ("triage.json", "triage"),
}


def main(argv: list[str] | None = None) -> int:
    """Dispatch a query subcommand."""
    parser = argparse.ArgumentParser(description="Read-only queries over the output directory.")
    parser.add_argument("output_dir", help="the testmap_output directory")
    sub = parser.add_subparsers(dest="command", required=True)
    for kind in _PER_FILE:
        p = sub.add_parser(kind, help=f"print one symbol's {kind} record")
        p.add_argument("symbol_id")
    sub.add_parser("stale", help="list stale or unanalyzed symbol IDs")
    sub.add_parser("summary", help="print count summary (total, analyzed, stale, by priority)")

    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir).resolve()
    if args.command in _PER_FILE:
        return _read_record(output_dir, args.command, args.symbol_id)
    if args.command == "stale":
        return _stale(output_dir)
    return _summary(output_dir)


def _read_record(output_dir: Path, file_kind: str, symbol_id: str) -> int:
    """Print one symbol's record from a per-symbol data file."""
    filename, schema_name = _PER_FILE[file_kind]
    path = output_dir / filename
    if not path.is_file():
        print(f"error: {filename} not found in {output_dir}", file=sys.stderr)
        return 1
    record = schema_lib.read_json(path, schema_name).get(symbol_id)
    if record is None:
        print(f"error: no {file_kind} entry for symbol: {symbol_id}", file=sys.stderr)
        return 1
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


def _stale(output_dir: Path) -> int:
    """List symbols that are stale or have no analysis yet."""
    status = _classify(output_dir)
    for symbol_id in sorted(status):
        if status[symbol_id] != staleness_lib.UP_TO_DATE:
            print(symbol_id)
    return 0


def _summary(output_dir: Path) -> int:
    """Print a JSON count summary across index, triage, and analysis."""
    index = schema_lib.read_json(output_dir / "index.json", "index")
    triage = schema_lib.read_json(output_dir / "triage.json", "triage")
    analysis = analysis_lib.load_analysis(output_dir / "analysis.json")
    status = _classify(output_dir)
    by_priority = {"high": 0, "medium": 0, "low": 0}
    for symbol_id in index:
        priority = triage.get(symbol_id, {}).get("priority")
        if priority in by_priority:
            by_priority[priority] += 1
    summary = {
        "total": len(index),
        "analyzed": len(analysis),
        "stale": sum(1 for s in status.values() if s != staleness_lib.UP_TO_DATE),
        "by_priority": by_priority,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _classify(output_dir: Path) -> dict[str, str]:
    """Classify staleness for every symbol from the data files in ``output_dir``."""
    index = schema_lib.read_json(output_dir / "index.json", "index")
    analysis = analysis_lib.load_analysis(output_dir / "analysis.json")
    return staleness_lib.classify_all(index, analysis, output_dir.parent)


if __name__ == "__main__":
    sys.exit(main())

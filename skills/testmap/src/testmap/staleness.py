"""CLI for stage 3: report staleness + pre-analysis summary, and write scope.json.

Usage:
    uv run staleness summary <target_dir>
    uv run staleness write-scope <target_dir> <mode> [SYMBOL_ID ...]

``summary`` classifies every symbol (no-analysis / stale / up-to-date, PRD 3.1) and
prints the pre-analysis summary (PRD 4.4) plus per-symbol status JSON, which the
agent uses to present scope options. ``write-scope`` records the user-confirmed
scope (PRD 4.5-4.6) to the ephemeral scope.json; the agent calls it after
confirmation. Mode ``custom`` requires the explicit symbol IDs.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from testmap import schema_lib, staleness_lib
from testmap.paths_lib import data_file, temp_dir

_LARGE_SCOPE_WARNING = 300


def main(argv: list[str] | None = None) -> int:
    """Dispatch to the summary or write-scope subcommand."""
    parser = argparse.ArgumentParser(description="Staleness summary and scope selection.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_summary = sub.add_parser("summary", help="print the pre-analysis summary and per-symbol status")
    p_summary.add_argument("target_dir", help="directory analyzed by discover and triage")

    p_scope = sub.add_parser("write-scope", help="record the confirmed analysis scope")
    p_scope.add_argument("target_dir", help="directory analyzed by discover and triage")
    p_scope.add_argument("mode", choices=["all", "high_only", "custom"], help="which symbols to analyze")
    p_scope.add_argument("symbol_ids", nargs="*", help="symbol IDs (required for custom mode)")

    args = parser.parse_args(argv)
    target_dir = Path(args.target_dir).resolve()
    if args.command == "summary":
        return _summary(target_dir)
    return _write_scope(target_dir, args.mode, args.symbol_ids)


def _summary(target_dir: Path) -> int:
    """Classify staleness and print the pre-analysis summary plus per-symbol status."""
    index_path = data_file(target_dir, "index.json")
    triage_path = data_file(target_dir, "triage.json")
    if not index_path.is_file() or not triage_path.is_file():
        print("error: run discover and triage first", file=sys.stderr)
        return 1

    index = schema_lib.read_json(index_path, "index")
    triage = schema_lib.read_json(triage_path, "triage")
    prior = _load_prior_analysis(target_dir)
    status = staleness_lib.classify_all(index, prior, target_dir)

    _print_summary(index, triage, status, target_dir)
    print("\nper_symbol_status:")
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


def _write_scope(target_dir: Path, mode: str, symbol_ids: list[str]) -> int:
    """Write the confirmed scope.json (PRD 4.5-4.6)."""
    if mode == "custom" and not symbol_ids:
        print("error: custom mode requires explicit symbol IDs", file=sys.stderr)
        return 1

    scope_path = temp_dir(target_dir) / "scope.json"
    scope = {"mode": mode, "symbol_ids": _resolve_symbol_ids(target_dir, mode, symbol_ids)}
    schema_lib.write_json(scope_path, scope, "scope")
    print(f"scope written ({mode}, {len(scope['symbol_ids'])} symbols) -> {scope_path}")
    return 0


def _resolve_symbol_ids(target_dir: Path, mode: str, custom_ids: list[str]) -> list[str]:
    """Resolve the symbol IDs a scope mode selects."""
    if mode == "custom":
        return sorted(set(custom_ids))
    index = schema_lib.read_json(data_file(target_dir, "index.json"), "index")
    if mode == "all":
        return sorted(index.keys())
    triage = schema_lib.read_json(data_file(target_dir, "triage.json"), "triage")
    return sorted(sid for sid in index if triage.get(sid, {}).get("priority") == "high")


def _load_prior_analysis(target_dir: Path) -> dict[str, dict]:
    """Load a prior analysis.json if present, else an empty mapping."""
    analysis_path = data_file(target_dir, "analysis.json")
    if not analysis_path.is_file():
        return {}
    with analysis_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _print_summary(
    index: dict[str, dict],
    triage: dict[str, dict],
    status: dict[str, str],
    target_dir: Path,
) -> None:
    """Print the PRD 4.4 pre-analysis summary."""
    kinds = Counter(s["kind"] for s in index.values())
    buckets = Counter(t["priority"] for t in triage.values())
    states = Counter(status.values())
    total = len(index)

    print(f"Pre-analysis summary for {target_dir}")
    print(f"  Total symbols: {total} "
          f"({kinds['function']} functions, {kinds['method']} methods, {kinds['class']} classes)")
    print(f"  Priority: {buckets['high']} high, {buckets['medium']} medium, {buckets['low']} low")
    print(f"  Analysis state: {states[staleness_lib.NO_ANALYSIS]} no-analysis, "
          f"{states[staleness_lib.STALE]} stale, {states[staleness_lib.UP_TO_DATE]} up-to-date")
    to_analyze = states[staleness_lib.NO_ANALYSIS] + states[staleness_lib.STALE]
    print(f"  Needs analysis: {to_analyze}")
    if to_analyze >= _LARGE_SCOPE_WARNING:
        print(f"  WARNING: {to_analyze} symbols need analysis — this may take significant "
              f"time and tokens. Consider analyzing high-priority symbols first.")
    print("  NOTE: output will be written to testmap_output/ and will overwrite existing "
          "output. Commit any changes you want to keep before proceeding.")


if __name__ == "__main__":
    sys.exit(main())

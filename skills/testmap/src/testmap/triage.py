"""CLI for stage 2: score each indexed symbol by risk and write triage.json.

Usage:
    uv run triage <target_dir>

Reads index.json, computes the six PRD 4.1 signals (sensitivity, complexity,
error paths, public API, git churn, no-analysis), and writes one triage record
per symbol. Pure function of its inputs (architecture §4).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from testmap import churn_lib, schema_lib, triage_lib
from testmap.paths_lib import SKILL_ROOT, data_file

_SENSITIVITY_FILE = SKILL_ROOT / "sensitivity_keywords.md"


def main(argv: list[str] | None = None) -> int:
    """Entry point: read index.json and write triage.json."""
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        print("usage: triage <target_dir>", file=sys.stderr)
        return 1

    target_dir = Path(argv[0]).resolve()
    index_path = data_file(target_dir, "index.json")
    if not index_path.is_file():
        print(f"error: index not found, run discover first: {index_path}", file=sys.stderr)
        return 1

    index = schema_lib.read_json(index_path, "index")
    keywords = triage_lib.parse_sensitivity_keywords(_SENSITIVITY_FILE.read_text(encoding="utf-8"))
    churn = _collect_churn(target_dir, index)
    prior_ids = _prior_analysis_ids(target_dir)

    triage = {
        symbol_id: triage_lib.triage_symbol(
            symbol,
            sensitivity_matches=triage_lib.match_sensitivity(
                symbol["qualified_name"], symbol["file_path"], keywords
            ),
            churn=churn.get(symbol["file_path"]),
            has_prior_analysis=symbol_id in prior_ids,
        )
        for symbol_id, symbol in index.items()
    }

    triage_path = data_file(target_dir, "triage.json")
    schema_lib.write_json(triage_path, triage, "triage")
    _print_summary(triage, triage_path, churn_available=bool(churn))
    return 0


def _collect_churn(target_dir: Path, index: dict[str, dict]) -> dict[str, int]:
    """Return per-file churn keyed by index-relative path, or empty if not a git repo.

    Index paths are relative to ``target_dir``; git reports paths relative to the
    repo root, so churn is requested with the repo-root prefix and mapped back.
    """
    if not churn_lib.is_git_repo(target_dir):
        return {}
    prefix = _repo_relative_prefix(target_dir)
    file_paths = {symbol["file_path"] for symbol in index.values()}
    repo_paths = {f"{prefix}{path}" for path in file_paths}
    repo_churn = churn_lib.file_churn(target_dir, repo_paths)
    return {path: repo_churn.get(f"{prefix}{path}", 0) for path in file_paths}


def _repo_relative_prefix(target_dir: Path) -> str:
    """Return target_dir's path within its git repo as a path prefix (or empty)."""
    repo_root = churn_lib.repo_toplevel(target_dir)
    if repo_root is None or target_dir == repo_root:
        return ""
    return f"{target_dir.relative_to(repo_root).as_posix()}/"


def _prior_analysis_ids(target_dir: Path) -> set[str]:
    """Return the set of symbol IDs present in a prior analysis.json, if any."""
    analysis_path = data_file(target_dir, "analysis.json")
    if not analysis_path.is_file():
        return set()
    with analysis_path.open(encoding="utf-8") as handle:
        return set(json.load(handle).keys())


def _print_summary(triage: dict[str, dict], triage_path: Path, *, churn_available: bool) -> None:
    """Print triage counts by priority bucket."""
    buckets = Counter(record["priority"] for record in triage.values())
    note = "" if churn_available else " (churn unavailable: not a git repo)"
    print(
        f"triaged {len(triage)} symbols "
        f"({buckets['high']} high, {buckets['medium']} medium, {buckets['low']} low) "
        f"-> {triage_path}{note}"
    )


if __name__ == "__main__":
    sys.exit(main())

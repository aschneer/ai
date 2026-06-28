"""CLI for stage 6 (code half): compute metrics.json and meta.json.

Usage:
    uv run report <target_dir>

Reads index.json, triage.json, analysis.json, and optionally mutation.json, then
writes metrics.json (composite score, grade, KPIs — PRD 8.2.1/8.2.2) and meta.json
(run metadata — PRD 9.3). The agent writes report_content.json and the static
rendering assets are copied separately; this command covers only the deterministic
computed outputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from testmap import analysis_lib, report_lib, schema_lib
from testmap.paths_lib import data_file, temp_dir


def main(argv: list[str] | None = None) -> int:
    """Entry point: write metrics.json and meta.json for a completed analysis."""
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        print("usage: report <target_dir>", file=sys.stderr)
        return 1

    target_dir = Path(argv[0]).resolve()
    index_path = data_file(target_dir, "index.json")
    if not index_path.is_file():
        print("error: run discover, triage, and analysis first", file=sys.stderr)
        return 1

    index = schema_lib.read_json(index_path, "index")
    triage = schema_lib.read_json(data_file(target_dir, "triage.json"), "triage")
    analysis = analysis_lib.load_analysis(data_file(target_dir, "analysis.json"))
    mutation = _load_mutation(target_dir)

    metrics = report_lib.compute_metrics(analysis, triage, mutation)
    schema_lib.write_json(data_file(target_dir, "metrics.json"), metrics, "metrics")

    meta = report_lib.assemble_meta(
        target_dir,
        total_symbols=len(index),
        analyzed_this_run=len(analysis),
        scope_mode=_scope_mode(target_dir),
    )
    schema_lib.write_json(data_file(target_dir, "meta.json"), meta, "meta")

    print(
        f"report metrics: score {metrics['composite_score']} ({metrics['grade']}), "
        f"{metrics['gap_cells']} gaps across {metrics['symbols_analyzed']} symbols "
        f"-> {data_file(target_dir, 'metrics.json')}"
    )
    return 0


def _load_mutation(target_dir: Path) -> dict[str, dict] | None:
    """Load mutation.json if mutation testing was run, else None."""
    mutation_path = data_file(target_dir, "mutation.json")
    if not mutation_path.is_file():
        return None
    return schema_lib.read_json(mutation_path, "mutation")


def _scope_mode(target_dir: Path) -> str:
    """Return the scope mode from scope.json, defaulting to 'all' if absent."""
    scope_path = temp_dir(target_dir) / "scope.json"
    if not scope_path.is_file():
        return "all"
    with scope_path.open(encoding="utf-8") as handle:
        return json.load(handle).get("mode", "all")


if __name__ == "__main__":
    sys.exit(main())

"""Compute report metrics (score, grade, KPIs) and assemble run metadata.

The composite-score formula (PRD 8.2.1) is exact arithmetic, so it lives in code
and is written to metrics.json; the rendering layer displays it rather than
recomputing. meta.json carries run metadata (PRD 9.3).
"""

from __future__ import annotations

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from testmap import churn_lib

# Composite-score weights and caps (PRD 8.2.1.1).
_COVERAGE_WEIGHT = 100
_BRITTLE_PENALTY = 20
_UNSPECIFIED_PENALTY = 10

# Grade thresholds as (minimum_score, label), highest first (PRD 8.2.1.2).
_GRADES = (
    (90, "Excellent"),
    (75, "Good"),
    (50, "Fair"),
    (25, "Poor"),
    (0, "Critical"),
)


def compute_metrics(
    analysis: dict[str, dict[str, Any]],
    triage: dict[str, dict[str, Any]],
    mutation: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute the composite score, grade, and KPI aggregates from analysis data."""
    tallies = _tally_cells(analysis)
    coverage_pct = _coverage_pct(tallies)
    score = _composite_score(coverage_pct, tallies)
    return {
        "composite_score": round(score, 2),
        "grade": _grade(score),
        "coverage_pct": round(coverage_pct, 4),
        "total_cells": tallies["total"],
        "covered_cells": tallies["covered"],
        "gap_cells": tallies["gap"],
        "unspecified_cells": tallies["unspecified"],
        "total_covering_tests": tallies["covering_tests"],
        "brittle_test_count": tallies["brittle"],
        "symbols_analyzed": len(analysis),
        "high_priority_with_gaps": _high_priority_with_gaps(analysis, triage),
        "mutation_score": _mutation_score(mutation),
    }


def _tally_cells(analysis: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Count cells by status and covering/brittle tests across all analyzed symbols."""
    tally = {"total": 0, "covered": 0, "gap": 0, "unspecified": 0,
             "covering_tests": 0, "brittle": 0}
    for entry in analysis.values():
        for cell in entry.get("behavior_matrix", []):
            tally["total"] += 1
            tally[cell["status"]] += 1
            for test in cell.get("covering_tests", []):
                tally["covering_tests"] += 1
                if test.get("brittle"):
                    tally["brittle"] += 1
    return tally


def _coverage_pct(tally: dict[str, int]) -> float:
    """covered / (total - unspecified); 0 when the denominator is 0 (PRD 8.2.1.1)."""
    denominator = tally["total"] - tally["unspecified"]
    if denominator <= 0:
        return 0.0
    return tally["covered"] / denominator


def _composite_score(coverage_pct: float, tally: dict[str, int]) -> float:
    """Apply the PRD 8.2.1.1 formula and clamp to 0..100."""
    base = coverage_pct * _COVERAGE_WEIGHT
    brittle_penalty = _ratio(tally["brittle"], tally["covering_tests"]) * _BRITTLE_PENALTY
    unspecified_penalty = _ratio(tally["unspecified"], tally["total"]) * _UNSPECIFIED_PENALTY
    return _clamp(base - brittle_penalty - unspecified_penalty, 0, 100)


def _high_priority_with_gaps(
    analysis: dict[str, dict[str, Any]], triage: dict[str, dict[str, Any]]
) -> int:
    """Count high-priority symbols having at least one gap cell (PRD 8.2.2.4)."""
    count = 0
    for symbol_id, entry in analysis.items():
        if triage.get(symbol_id, {}).get("priority") != "high":
            continue
        if any(cell["status"] == "gap" for cell in entry.get("behavior_matrix", [])):
            count += 1
    return count


def _mutation_score(mutation: dict[str, dict[str, Any]] | None) -> float | None:
    """Aggregate killed / total mutants, or None if mutation testing was not run."""
    if not mutation:
        return None
    killed = sum(record["killed"] for record in mutation.values())
    total = sum(record["killed"] + record["survived"] for record in mutation.values())
    return round(killed / total, 4) if total > 0 else None


def _ratio(numerator: int, denominator: int) -> float:
    """Safe ratio: 0 when the denominator is 0."""
    return numerator / denominator if denominator > 0 else 0.0


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a value to the inclusive range."""
    return max(low, min(high, value))


def _grade(score: float) -> str:
    """Map a composite score to its grade label (PRD 8.2.1.2)."""
    for minimum, label in _GRADES:
        if score >= minimum:
            return label
    return _GRADES[-1][1]


def assemble_meta(
    target_dir: Path,
    *,
    total_symbols: int,
    analyzed_this_run: int,
    scope_mode: str,
    mutation_tools: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the run metadata record (PRD 9.3)."""
    tool_versions = {"tree-sitter": _package_version("tree-sitter")}
    if mutation_tools:
        tool_versions.update(mutation_tools)
    return {
        "target_dir": str(target_dir),
        "repo_remote_url": _git_remote_url(target_dir),
        "git_commit": _git_commit(target_dir),
        "run_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope_mode": scope_mode,
        "total_symbols": total_symbols,
        "analyzed_this_run": analyzed_this_run,
        "tool_versions": tool_versions,
    }


def _git_commit(target_dir: Path) -> str | None:
    """Return the target repo's current commit hash, or None if not a git repo."""
    result = churn_lib.run_git(target_dir, ["rev-parse", "HEAD"])
    return result.strip() if result else None


def _git_remote_url(target_dir: Path) -> str | None:
    """Return the target repo's origin remote URL, or None if unavailable."""
    result = churn_lib.run_git(target_dir, ["config", "--get", "remote.origin.url"])
    return result.strip() if result else None


def _package_version(name: str) -> str:
    """Return an installed package version, or 'unknown' if not found."""
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"

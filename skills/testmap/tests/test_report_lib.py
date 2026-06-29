"""Tests for report metrics and run-metadata assembly."""

from __future__ import annotations

from pathlib import Path

from testmap import report_lib


def _cell(status: str, brittle: int = 0, covering: int = 0) -> dict:
    cell = {"input_class": "i", "expected_behavior": "b", "status": status}
    if status == "covered":
        cell["covering_tests"] = [
            {"test_name": f"t{n}", "brittle": n < brittle} for n in range(covering)
        ]
    return cell


def _entry(cells: list[dict]) -> dict:
    return {
        "spec": "s",
        "behavior_matrix": cells,
        "test_difficulty": {"rating": "low", "signals_note": "n"},
        "body_hash": "h",
        "covering_test_hashes": {},
        "timestamp": "2026-06-29T00:00:00Z",
    }


def test_perfect_coverage_scores_100_excellent() -> None:
    analysis = {"s": _entry([_cell("covered", 0, 1), _cell("covered", 0, 1)])}
    metrics = report_lib.compute_metrics(analysis, {})
    assert metrics["composite_score"] == 100.0
    assert metrics["grade"] == "Excellent"


def test_coverage_excludes_unspecified_from_denominator() -> None:
    # 1 covered, 1 gap, 1 unspecified => 1 / (3 - 1) = 0.5
    analysis = {"s": _entry([_cell("covered", 0, 1), _cell("gap"), _cell("unspecified")])}
    metrics = report_lib.compute_metrics(analysis, {})
    assert metrics["coverage_pct"] == 0.5


def test_brittle_and_unspecified_penalties_apply() -> None:
    # cov=0.5 -> base 50; brittle 1/2 -> -10; unspec 1/3 -> -3.33 => 36.67
    analysis = {"s": _entry([_cell("covered", 1, 2), _cell("gap"), _cell("unspecified")])}
    metrics = report_lib.compute_metrics(analysis, {})
    assert abs(metrics["composite_score"] - 36.67) < 0.01


def test_empty_analysis_scores_zero_critical() -> None:
    metrics = report_lib.compute_metrics({}, {})
    assert metrics["composite_score"] == 0.0
    assert metrics["grade"] == "Critical"
    assert metrics["coverage_pct"] == 0.0


def test_cell_tallies() -> None:
    analysis = {"s": _entry([_cell("covered", 0, 1), _cell("gap"), _cell("unspecified")])}
    metrics = report_lib.compute_metrics(analysis, {})
    assert metrics["total_cells"] == 3
    assert metrics["covered_cells"] == 1
    assert metrics["gap_cells"] == 1
    assert metrics["unspecified_cells"] == 1


def test_brittle_test_count_tallied() -> None:
    analysis = {"s": _entry([_cell("covered", 2, 3)])}
    metrics = report_lib.compute_metrics(analysis, {})
    assert metrics["brittle_test_count"] == 2
    assert metrics["total_covering_tests"] == 3


def test_high_priority_with_gaps_counts_only_high_with_a_gap() -> None:
    analysis = {
        "hi": _entry([_cell("gap")]),
        "hi_clean": _entry([_cell("covered", 0, 1)]),
        "lo": _entry([_cell("gap")]),
    }
    triage = {
        "hi": {"priority": "high"},
        "hi_clean": {"priority": "high"},
        "lo": {"priority": "low"},
    }
    metrics = report_lib.compute_metrics(analysis, triage)
    assert metrics["high_priority_with_gaps"] == 1


def test_grade_bands() -> None:
    # Drive coverage to hit each band via covered/gap ratios on single-test cells.
    def score_for(covered: int, total: int) -> float:
        cells = [_cell("covered", 0, 1)] * covered + [_cell("gap")] * (total - covered)
        return report_lib.compute_metrics({"s": _entry(cells)}, {})["grade"]

    assert score_for(10, 10) == "Excellent"   # 100
    assert score_for(8, 10) == "Good"         # 80
    assert score_for(6, 10) == "Fair"         # 60
    assert score_for(3, 10) == "Poor"         # 30
    assert score_for(1, 10) == "Critical"     # 10


def test_assemble_meta_fields(tmp_path: Path) -> None:
    meta = report_lib.assemble_meta(
        tmp_path, total_symbols=5, analyzed_this_run=2, scope_mode="all"
    )
    assert meta["target_dir"] == str(tmp_path)
    assert meta["total_symbols"] == 5
    assert meta["analyzed_this_run"] == 2
    assert meta["scope_mode"] == "all"
    assert meta["run_timestamp"].endswith("Z")
    assert "tree-sitter" in meta["tool_versions"]


def test_assemble_meta_null_git_outside_repo(tmp_path: Path) -> None:
    meta = report_lib.assemble_meta(
        tmp_path, total_symbols=1, analyzed_this_run=1, scope_mode="all"
    )
    assert meta["git_commit"] is None

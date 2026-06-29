"""Integration tests driving the pipeline CLIs through their main() entry points."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from testmap import analysis_cli, discover, query, report, staleness, triage

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample"


@pytest.fixture
def target(tmp_path: Path) -> Path:
    dest = tmp_path / "sample"
    shutil.copytree(FIXTURE, dest)
    return dest


def _output(target: Path) -> Path:
    return target / "testmap_output"


def _read(path: Path) -> dict:
    return json.loads(path.read_text())


def test_discover_writes_index(target: Path) -> None:
    assert discover.main([str(target)]) == 0
    index = _read(_output(target) / "index.json")
    names = {v["qualified_name"] for v in index.values()}
    assert {"add", "Calc", "Calc.mul"} <= names


def test_discover_missing_target_errors() -> None:
    assert discover.main(["/no/such/dir/xyz"]) == 1


def test_discover_test_glob_flags_test_files(target: Path) -> None:
    discover.main([str(target), "--test-glob", "tests/**"])
    index = _read(_output(target) / "index.json")
    test_syms = [v for v in index.values() if v["is_test_file"]]
    assert test_syms and all("tests/" in v["file_path"] for v in test_syms)


def test_discover_respects_config_exclude(target: Path) -> None:
    (target / "src" / "vendored.py").write_text("def vendored(): pass\n")
    (target / "testmap_config.json").write_text('{"exclude": ["src/vendored.py"]}')
    discover.main([str(target)])
    index = _read(_output(target) / "index.json")
    assert not any("vendored" in v["qualified_name"] for v in index.values())


def test_discover_installs_output_gitignore(target: Path) -> None:
    discover.main([str(target)])
    assert (_output(target) / ".gitignore").read_text().strip() == "temp/"


def test_triage_requires_index_first(target: Path) -> None:
    assert triage.main([str(target)]) == 1


def test_triage_writes_buckets(target: Path) -> None:
    discover.main([str(target)])
    assert triage.main([str(target)]) == 0
    triage_data = _read(_output(target) / "triage.json")
    assert all(t["priority"] in ("high", "medium", "low") for t in triage_data.values())


def test_staleness_summary_runs(target: Path) -> None:
    discover.main([str(target)])
    triage.main([str(target)])
    assert staleness.main(["summary", str(target)]) == 0


def test_write_scope_all_then_query_stale(target: Path, capsys) -> None:
    discover.main([str(target)])
    triage.main([str(target)])
    assert staleness.main(["write-scope", str(target), "all"]) == 0
    scope = _read(_output(target) / "temp" / "scope.json")
    assert scope["mode"] == "all"
    assert scope["symbol_ids"]


def test_write_scope_custom_requires_ids(target: Path) -> None:
    discover.main([str(target)])
    assert staleness.main(["write-scope", str(target), "custom"]) == 1


def test_full_pipeline_through_report(target: Path) -> None:
    discover.main([str(target)])
    triage.main([str(target)])
    # Write one analysis entry so the report has data.
    index = _read(_output(target) / "index.json")
    sid = next(k for k, v in index.items() if v["qualified_name"] == "add")
    entry = {
        "spec": "adds a and b",
        "behavior_matrix": [
            {"input_class": "valid", "expected_behavior": "sum", "status": "covered",
             "covering_tests": [{"test_name": "test_add", "brittle": False}]},
            {"input_class": "negative a", "expected_behavior": "raises", "status": "gap",
             "gap_note": "no test", "test_prescription": "pass a<0, assert ValueError"},
        ],
        "test_difficulty": {"rating": "low", "signals_note": "pure"},
        "body_hash": index[sid]["body_hash"],
        "covering_test_hashes": {},
        "timestamp": "2026-06-29T00:00:00Z",
    }
    analysis_cli.main(["write", str(_output(target) / "analysis.json"), sid, json.dumps(entry)])

    assert report.main([str(target)]) == 0
    metrics = _read(_output(target) / "metrics.json")
    assert 0 <= metrics["composite_score"] <= 100
    assert (_output(target) / "report" / "report.html").is_file()
    assert (_output(target) / "README.md").is_file()
    assert (_output(target) / "serve.sh").stat().st_mode & 0o111  # executable


def test_report_requires_index(target: Path) -> None:
    assert report.main([str(target)]) == 1

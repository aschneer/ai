"""Tests for the analysis-cli (write path) and query (read path) CLIs."""

from __future__ import annotations

import io
import json
import shutil
from pathlib import Path

import pytest

from testmap import analysis_cli, discover, query, triage

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample"


@pytest.fixture
def analyzed(tmp_path: Path) -> tuple[Path, str]:
    """A target with index + triage built and one analysis entry written."""
    target = tmp_path / "sample"
    shutil.copytree(FIXTURE, target)
    discover.main([str(target)])
    triage.main([str(target)])
    out = target / "testmap_output"
    index = json.loads((out / "index.json").read_text())
    sid = next(k for k, v in index.items() if v["qualified_name"] == "add")
    entry = {
        "spec": "adds",
        "behavior_matrix": [],
        "test_difficulty": {"rating": "low", "signals_note": "n"},
        "body_hash": index[sid]["body_hash"],
        "covering_test_hashes": {},
        "timestamp": "2026-06-29T00:00:00Z",
    }
    analysis_cli.main(["write", str(out / "analysis.json"), sid, json.dumps(entry)])
    return target, sid


def test_write_then_read_entry(analyzed, capsys) -> None:
    target, sid = analyzed
    ap = str(target / "testmap_output" / "analysis.json")
    assert analysis_cli.main(["read", ap, sid]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["spec"] == "adds"


def test_write_reads_json_from_stdin(analyzed, monkeypatch) -> None:
    target, sid = analyzed
    ap = str(target / "testmap_output" / "analysis.json")
    entry = {
        "spec": "via stdin",
        "behavior_matrix": [],
        "test_difficulty": {"rating": "low", "signals_note": "n"},
        "body_hash": "h",
        "covering_test_hashes": {},
        "timestamp": "2026-06-29T00:00:00Z",
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(entry)))
    assert analysis_cli.main(["write", ap, "x::y", "-"]) == 0


def test_write_invalid_entry_returns_error(analyzed, capsys) -> None:
    target, _ = analyzed
    ap = str(target / "testmap_output" / "analysis.json")
    assert analysis_cli.main(["write", ap, "x::y", '{"spec": "incomplete"}']) == 1
    assert capsys.readouterr().err  # faults reported


def test_write_rejects_malformed_json(analyzed, capsys) -> None:
    target, _ = analyzed
    ap = str(target / "testmap_output" / "analysis.json")
    assert analysis_cli.main(["write", ap, "x::y", "{not json"]) == 1


def test_read_missing_entry_errors(analyzed) -> None:
    target, _ = analyzed
    ap = str(target / "testmap_output" / "analysis.json")
    assert analysis_cli.main(["read", ap, "no::such"]) == 1


def test_list_keys(analyzed, capsys) -> None:
    target, sid = analyzed
    ap = str(target / "testmap_output" / "analysis.json")
    analysis_cli.main(["list-keys", ap])
    assert sid in capsys.readouterr().out


def test_query_index_record(analyzed, capsys) -> None:
    target, sid = analyzed
    out = str(target / "testmap_output")
    assert query.main([out, "index", sid]) == 0
    assert json.loads(capsys.readouterr().out)["qualified_name"] == "add"


def test_query_triage_record(analyzed, capsys) -> None:
    target, sid = analyzed
    out = str(target / "testmap_output")
    assert query.main([out, "triage", sid]) == 0
    assert "priority" in json.loads(capsys.readouterr().out)


def test_query_missing_record_errors(analyzed) -> None:
    target, _ = analyzed
    out = str(target / "testmap_output")
    assert query.main([out, "index", "no::such"]) == 1


def test_query_stale_excludes_analyzed(analyzed, capsys) -> None:
    target, sid = analyzed
    out = str(target / "testmap_output")
    query.main([out, "stale"])
    stale = capsys.readouterr().out.split()
    assert sid not in stale  # the analyzed, up-to-date symbol is not stale


def test_query_summary_counts(analyzed, capsys) -> None:
    target, _ = analyzed
    out = str(target / "testmap_output")
    query.main([out, "summary"])
    summary = json.loads(capsys.readouterr().out)
    assert summary["analyzed"] == 1
    assert summary["total"] >= 3

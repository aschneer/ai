"""Tests for validating and assembling agent-produced analysis entries."""

from __future__ import annotations

from pathlib import Path

from testmap import analysis_lib


def _entry(body_hash: str = "h") -> dict:
    return {
        "spec": "does a thing",
        "behavior_matrix": [
            {"input_class": "i", "expected_behavior": "b", "status": "gap",
             "gap_note": "no test", "test_prescription": "pass x, assert y"}
        ],
        "test_difficulty": {"rating": "low", "signals_note": "pure"},
        "body_hash": body_hash,
        "covering_test_hashes": {},
        "timestamp": "2026-06-29T00:00:00Z",
    }


def test_load_missing_returns_empty(tmp_path: Path) -> None:
    assert analysis_lib.load_analysis(tmp_path / "nope.json") == {}


def test_write_then_read_entry(tmp_path: Path) -> None:
    path = tmp_path / "analysis.json"
    errors = analysis_lib.write_entry(path, "a::b", _entry())
    assert errors == []
    assert analysis_lib.read_entry(path, "a::b") == _entry()


def test_write_creates_file_when_absent(tmp_path: Path) -> None:
    path = tmp_path / "analysis.json"
    analysis_lib.write_entry(path, "a::b", _entry())
    assert path.is_file()


def test_write_upserts_without_dropping_others(tmp_path: Path) -> None:
    path = tmp_path / "analysis.json"
    analysis_lib.write_entry(path, "a::b", _entry("h1"))
    analysis_lib.write_entry(path, "c::d", _entry("h2"))
    assert set(analysis_lib.load_analysis(path)) == {"a::b", "c::d"}


def test_read_missing_entry_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "analysis.json"
    analysis_lib.write_entry(path, "a::b", _entry())
    assert analysis_lib.read_entry(path, "x::y") is None


def test_validate_entry_collects_all_faults() -> None:
    errors = analysis_lib.validate_entry("a::b", {"spec": "only"})
    assert len(errors) > 1


def test_write_rejects_invalid_entry_without_writing(tmp_path: Path) -> None:
    path = tmp_path / "analysis.json"
    errors = analysis_lib.write_entry(path, "a::b", {"spec": "incomplete"})
    assert errors
    # Nothing persisted on a rejected write.
    assert not path.exists()

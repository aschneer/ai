"""Tests for schema loading and schema-validated JSON read/write."""

from __future__ import annotations

from pathlib import Path

import pytest

from testmap import schema_lib

_VALID_SYMBOL = {
    "qualified_name": "f",
    "kind": "function",
    "file_path": "a.py",
    "start_line": 1,
    "end_line": 3,
    "language": "python",
    "signature": "def f():",
    "body_hash": "x",
    "signature_hash": "y",
    "cyclomatic_complexity": 1,
    "has_error_paths": False,
    "decorators": [],
    "visibility": "public",
    "is_test_file": False,
}


def test_load_schema_returns_mapping_with_id() -> None:
    schema = schema_lib.load_schema("index")
    assert schema["$id"] == "index.schema.yaml"


def test_validate_returns_empty_for_valid_document() -> None:
    assert schema_lib.validate({"a.py::f": _VALID_SYMBOL}, "index", label="doc") == []


def test_validate_collects_every_fault_in_one_pass() -> None:
    # A record missing many required fields should yield many errors, not just the first.
    errors = schema_lib.validate({"k": {"kind": "function"}}, "index", label="bad.json")
    assert len(errors) > 1
    assert all("bad.json" in e for e in errors)


def test_validate_does_not_raise_on_invalid() -> None:
    # validate reports; it never raises (the agent path depends on this).
    assert schema_lib.validate({"k": {}}, "index", label="x") != []


def test_validate_or_raise_raises_with_all_faults(tmp_path: Path) -> None:
    with pytest.raises(schema_lib.SchemaError) as exc:
        schema_lib.validate_or_raise({"k": {"kind": "function"}}, "index", label="bad")
    assert "\n" in str(exc.value)  # multiple faults joined


def test_validate_or_raise_passes_for_valid() -> None:
    schema_lib.validate_or_raise({"a.py::f": _VALID_SYMBOL}, "index", label="ok")


def test_write_then_read_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "index.json"
    doc = {"a.py::f": _VALID_SYMBOL}
    schema_lib.write_json(path, doc, "index")
    assert schema_lib.read_json(path, "index") == doc


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "deep" / "nested" / "index.json"
    schema_lib.write_json(path, {"a.py::f": _VALID_SYMBOL}, "index")
    assert path.is_file()


def test_write_rejects_invalid_document(tmp_path: Path) -> None:
    with pytest.raises(schema_lib.SchemaError):
        schema_lib.write_json(tmp_path / "bad.json", {"k": {}}, "index")


def test_read_rejects_invalid_document(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"k": {"kind": "nonsense"}}')
    with pytest.raises(schema_lib.SchemaError):
        schema_lib.read_json(path, "index")


def test_utc_timestamp_required_in_analysis() -> None:
    entry = {
        "spec": "s",
        "behavior_matrix": [],
        "test_difficulty": {"rating": "low", "signals_note": "n"},
        "body_hash": "h",
        "covering_test_hashes": {},
        "timestamp": "2026-06-29T00:00:00Z",
    }
    assert schema_lib.validate({"a::b": entry}, "analysis", label="ok") == []

    entry_offset = {**entry, "timestamp": "2026-06-29T00:00:00+05:00"}
    assert schema_lib.validate({"a::b": entry_offset}, "analysis", label="bad") != []

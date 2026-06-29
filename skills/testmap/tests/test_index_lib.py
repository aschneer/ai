"""Tests for symbol-ID minting, incremental merge, and index load/save."""

from __future__ import annotations

from pathlib import Path

from testmap import index_lib


def _record(name: str, signature: str, body_hash: str, **overrides) -> dict:
    record = {
        "qualified_name": name,
        "kind": "function",
        "file_path": "a.py",
        "start_line": 1,
        "end_line": 2,
        "language": "python",
        "signature": signature,
        "body_hash": body_hash,
        "signature_hash": "s",
        "cyclomatic_complexity": 1,
        "has_error_paths": False,
        "decorators": [],
        "visibility": "public",
        "is_test_file": False,
    }
    record.update(overrides)
    return record


def test_symbol_id_includes_path_name_signature() -> None:
    sid = index_lib.mint_symbol_id(_record("f", "def f(x):", "h"))
    assert sid == "a.py::f::deff(x):"


def test_overloads_get_distinct_ids() -> None:
    one = index_lib.mint_symbol_id(_record("f", "def f(x):", "h"))
    two = index_lib.mint_symbol_id(_record("f", "def f(x, y):", "h"))
    assert one != two


def test_symbol_id_is_whitespace_invariant() -> None:
    spaced = index_lib.mint_symbol_id(_record("f", "def  f( x ):", "h"))
    tight = index_lib.mint_symbol_id(_record("f", "def f(x):", "h"))
    assert spaced == tight


def test_build_index_keys_by_symbol_id() -> None:
    index = index_lib.build_index([_record("f", "def f():", "h")])
    assert list(index) == ["a.py::f::deff():"]


def test_merge_preserves_unchanged_entry_verbatim() -> None:
    existing = index_lib.build_index([_record("keep", "def keep():", "h", start_line=99)])
    discovered = index_lib.build_index([_record("keep", "def keep():", "h", start_line=1)])
    merged = index_lib.merge_index(existing, discovered)
    # Same body hash => the prior entry (start_line 99) is kept untouched.
    assert next(iter(merged.values()))["start_line"] == 99


def test_merge_updates_changed_entry() -> None:
    existing = index_lib.build_index([_record("c", "def c():", "old")])
    discovered = index_lib.build_index([_record("c", "def c():", "new")])
    merged = index_lib.merge_index(existing, discovered)
    assert next(iter(merged.values()))["body_hash"] == "new"


def test_merge_drops_deleted_and_adds_new() -> None:
    existing = index_lib.build_index([_record("gone", "def gone():", "h")])
    discovered = index_lib.build_index([_record("new", "def new():", "h")])
    merged = index_lib.merge_index(existing, discovered)
    names = {k.split("::")[1] for k in merged}
    assert names == {"new"}


def test_load_missing_index_returns_empty(tmp_path: Path) -> None:
    assert index_lib.load_index(tmp_path / "nope.json") == {}


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    index = index_lib.build_index([_record("f", "def f():", "h")])
    path = tmp_path / "index.json"
    index_lib.save_index(path, index)
    assert index_lib.load_index(path) == index

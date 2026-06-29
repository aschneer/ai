"""Tests for staleness classification."""

from __future__ import annotations

import hashlib
from pathlib import Path

from testmap import staleness_lib


def test_no_analysis_when_no_prior_entry(tmp_path: Path) -> None:
    index = {"s": {"body_hash": "h"}}
    status = staleness_lib.classify_all(index, {}, tmp_path)
    assert status["s"] == staleness_lib.NO_ANALYSIS


def test_up_to_date_when_body_and_tests_unchanged(tmp_path: Path) -> None:
    index = {"s": {"body_hash": "h"}}
    prior = {"s": {"body_hash": "h", "covering_test_hashes": {}}}
    status = staleness_lib.classify_all(index, prior, tmp_path)
    assert status["s"] == staleness_lib.UP_TO_DATE


def test_stale_when_body_hash_changed(tmp_path: Path) -> None:
    index = {"s": {"body_hash": "new"}}
    prior = {"s": {"body_hash": "old", "covering_test_hashes": {}}}
    status = staleness_lib.classify_all(index, prior, tmp_path)
    assert status["s"] == staleness_lib.STALE


def test_stale_when_covering_test_changed(tmp_path: Path) -> None:
    test_file = tmp_path / "t.py"
    test_file.write_text("changed")
    index = {"s": {"body_hash": "h"}}
    prior = {"s": {"body_hash": "h", "covering_test_hashes": {"t.py": "old-hash"}}}
    status = staleness_lib.classify_all(index, prior, tmp_path)
    assert status["s"] == staleness_lib.STALE


def test_up_to_date_when_covering_test_unchanged(tmp_path: Path) -> None:
    test_file = tmp_path / "t.py"
    test_file.write_text("orig")
    current = hashlib.sha256(b"orig").hexdigest()
    index = {"s": {"body_hash": "h"}}
    prior = {"s": {"body_hash": "h", "covering_test_hashes": {"t.py": current}}}
    status = staleness_lib.classify_all(index, prior, tmp_path)
    assert status["s"] == staleness_lib.UP_TO_DATE


def test_stale_when_covering_test_deleted(tmp_path: Path) -> None:
    # The test file no longer exists, so its hash differs from the recorded one.
    index = {"s": {"body_hash": "h"}}
    prior = {"s": {"body_hash": "h", "covering_test_hashes": {"gone.py": "some-hash"}}}
    status = staleness_lib.classify_all(index, prior, tmp_path)
    assert status["s"] == staleness_lib.STALE

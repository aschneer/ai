"""Classify each symbol's analysis as no-analysis, stale, or up-to-date (PRD 3.1).

A symbol is stale when its body hash changed since it was last analyzed, or when any
test file that covered it has changed since. Pure hash comparison — no judgment.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

NO_ANALYSIS = "no_analysis"
STALE = "stale"
UP_TO_DATE = "up_to_date"


def classify_all(
    index: dict[str, dict[str, Any]],
    prior_analysis: dict[str, dict[str, Any]],
    target_dir: Path,
) -> dict[str, str]:
    """Return the staleness status of every indexed symbol."""
    test_hash_cache: dict[str, str | None] = {}
    return {
        symbol_id: _classify(symbol, prior_analysis.get(symbol_id), target_dir, test_hash_cache)
        for symbol_id, symbol in index.items()
    }


def _classify(
    symbol: dict[str, Any],
    prior: dict[str, Any] | None,
    target_dir: Path,
    test_hash_cache: dict[str, str | None],
) -> str:
    """Classify one symbol against its prior analysis entry."""
    if prior is None:
        return NO_ANALYSIS
    if symbol["body_hash"] != prior.get("body_hash"):
        return STALE
    if _covering_tests_changed(prior.get("covering_test_hashes", {}), target_dir, test_hash_cache):
        return STALE
    return UP_TO_DATE


def _covering_tests_changed(
    prior_test_hashes: dict[str, str],
    target_dir: Path,
    test_hash_cache: dict[str, str | None],
) -> bool:
    """Whether any covering test file's current hash differs from the analyzed hash."""
    for test_path, analyzed_hash in prior_test_hashes.items():
        if _current_test_hash(test_path, target_dir, test_hash_cache) != analyzed_hash:
            return True
    return False


def _current_test_hash(
    test_path: str, target_dir: Path, cache: dict[str, str | None]
) -> str | None:
    """Hash a test file's current contents; None if it no longer exists. Cached per path."""
    if test_path not in cache:
        cache[test_path] = _hash_file(target_dir / test_path)
    return cache[test_path]


def _hash_file(path: Path) -> str | None:
    """Return the SHA-256 of a file's bytes, or None if it cannot be read."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None

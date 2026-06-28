"""Mint symbol IDs, merge discovery results incrementally, and load/save the index.

The index is a map of symbol_id -> symbol record and is always the complete symbol
set (PRD 9.2). Re-runs preserve unchanged entries verbatim and update only symbols
whose body hash changed (PRD 2.5).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from testmap import schema_lib

_INDEX_SCHEMA = "index"


def mint_symbol_id(record: dict[str, Any]) -> str:
    """Build the stable join key: relative_path::qualified_name::normalized_signature.

    The signature is whitespace-stripped so the key is invariant under reformatting
    but distinguishes overloads (decision 2026-06-28 21:30).
    """
    normalized_signature = re.sub(r"\s+", "", record["signature"])
    return f"{record['file_path']}::{record['qualified_name']}::{normalized_signature}"


def build_index(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Key a flat list of symbol records by minted symbol ID."""
    return {mint_symbol_id(record): record for record in records}


def merge_index(
    existing: dict[str, dict[str, Any]],
    discovered: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Merge a fresh discovery pass over a prior index (PRD 2.5, 9.2).

    The discovered set defines membership: symbols no longer present are dropped.
    A symbol whose body hash matches the prior entry is preserved verbatim; new or
    changed symbols take the freshly discovered record.
    """
    merged: dict[str, dict[str, Any]] = {}
    for symbol_id, record in discovered.items():
        prior = existing.get(symbol_id)
        if prior is not None and prior.get("body_hash") == record["body_hash"]:
            merged[symbol_id] = prior
        else:
            merged[symbol_id] = record
    return merged


def load_index(path: Path) -> dict[str, dict[str, Any]]:
    """Load and validate an existing index, or return empty if none exists."""
    if not path.is_file():
        return {}
    return schema_lib.read_json(path, _INDEX_SCHEMA)


def save_index(path: Path, index: dict[str, dict[str, Any]]) -> None:
    """Validate and write the index to disk."""
    schema_lib.write_json(path, index, _INDEX_SCHEMA)

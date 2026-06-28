"""Validate and assemble agent-produced analysis entries into analysis.json.

Stage 4 is agent-driven: the agent emits one analysis object per symbol, and this
library validates each against analysis.schema.yaml and stores it. The agent works
one entry at a time and never loads the whole file into its context (PRD 11), so
single-entry read/write are the primary operations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from testmap import schema_lib

_ANALYSIS_SCHEMA = "analysis"


def load_analysis(path: Path) -> dict[str, dict[str, Any]]:
    """Load analysis.json, or return empty if it does not exist yet."""
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_analysis(path: Path, analysis: dict[str, dict[str, Any]]) -> None:
    """Validate the full analysis map against the schema and write it."""
    schema_lib.write_json(path, analysis, _ANALYSIS_SCHEMA)


def read_entry(path: Path, symbol_id: str) -> dict[str, Any] | None:
    """Return one symbol's analysis entry, or None if absent."""
    return load_analysis(path).get(symbol_id)


def write_entry(path: Path, symbol_id: str, entry: dict[str, Any]) -> list[str]:
    """Validate and upsert one symbol's entry; return validation errors (empty if OK).

    Validates the single entry so the agent gets every fault at once and can fix
    them before re-running. The file is created on first write.
    """
    errors = validate_entry(symbol_id, entry)
    if errors:
        return errors
    analysis = load_analysis(path)
    analysis[symbol_id] = entry
    save_analysis(path, analysis)
    return []


def validate_entry(symbol_id: str, entry: dict[str, Any]) -> list[str]:
    """Validate one entry by checking it as a single-key analysis map.

    The schema reports the symbol_id as the error location, so the label only needs
    to mark these as entry-validation messages.
    """
    return schema_lib.validate({symbol_id: entry}, _ANALYSIS_SCHEMA, label="analysis entry")

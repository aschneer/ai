"""Paths to skill-local JSON Schema files."""

from __future__ import annotations

from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = SKILL_ROOT / "schemas"


def schedule_schema_path() -> Path:
    """Return the path to ``schemas/schedule.schema.yaml``."""
    return SCHEMAS_DIR / "schedule.schema.yaml"


def calendar_schema_path() -> Path:
    """Return the path to ``schemas/calendar.schema.yaml``."""
    return SCHEMAS_DIR / "calendar.schema.yaml"

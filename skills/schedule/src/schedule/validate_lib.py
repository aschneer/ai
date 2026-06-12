"""JSON Schema validation for schedule and calendar YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from schedule.paths_lib import calendar_schema_path, schedule_schema_path


def load_schema(path: Path) -> dict[str, Any]:
    """Load a JSON Schema file authored in YAML."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_document(data: Any, schema_path: Path, label: str) -> list[str]:
    """Validate ``data`` against a schema; return human-readable error strings."""
    schema = load_schema(schema_path)
    validator = Draft202012Validator(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "(root)"
        errors.append(f"{label}: {location}: {error.message}")
    return errors


def validate_schedule_file(schedule_path: Path, schedule_data: dict[str, Any]) -> list[str]:
    """Validate schedule YAML including the project-start milestone rule."""
    errors = validate_document(schedule_data, schedule_schema_path(), schedule_path.name)
    errors.extend(_validate_project_start_milestone(schedule_data))
    return errors


def validate_calendar_file(calendar_path: Path, calendar_data: dict[str, Any]) -> list[str]:
    """Validate calendar YAML against ``calendar.schema.yaml``."""
    return validate_document(calendar_data, calendar_schema_path(), calendar_path.name)


def _validate_project_start_milestone(schedule_data: dict[str, Any]) -> list[str]:
    """Require exactly one id-0 milestone at the top level."""
    items = schedule_data.get("items", [])
    starts = [item for item in items if isinstance(item, dict) and item.get("id") == 0]
    if len(starts) != 1:
        return ["schedule: items: expected exactly one item with id 0 (project start milestone)"]
    start = starts[0]
    if start.get("kind") != "milestone":
        return ["schedule: items: id 0 must be kind milestone"]
    return []

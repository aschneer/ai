"""Load JSON Schemas (authored in YAML) and read/write schema-validated JSON.

Every pipeline stage validates its input on read and its output on write
(architecture §8). A schema violation raises ``SchemaError`` naming the file and
the offending location, so a bad handoff fails fast at the boundary.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from testmap.paths_lib import schema_path

_FORMAT_CHECKER = FormatChecker()


class SchemaError(Exception):
    """A document failed schema validation."""


def load_schema(name: str) -> dict[str, Any]:
    """Load the schema ``schemas/<name>.schema.yaml``."""
    with schema_path(name).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate(data: Any, schema_name: str, *, label: str) -> list[str]:
    """Validate ``data`` against a named schema; return all faults as error strings.

    Returns an empty list when valid. Collecting every fault in one pass lets the
    agent fix all of them before re-running, instead of failing once per fault.
    ``label`` identifies the document in each message (typically the file path).
    """
    validator = Draft202012Validator(load_schema(schema_name), format_checker=_FORMAT_CHECKER)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "(root)"
        errors.append(f"{label}: {location}: {error.message}")
    return errors


def validate_or_raise(data: Any, schema_name: str, *, label: str) -> None:
    """Validate ``data``; raise ``SchemaError`` listing every fault if any.

    For code-produced handoffs, where an invalid document is a bug to fail fast on.
    """
    errors = validate(data, schema_name, label=label)
    if errors:
        raise SchemaError("\n".join(errors))


def read_json(path: Path, schema_name: str) -> Any:
    """Read JSON from ``path`` and validate it against a named schema."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    validate_or_raise(data, schema_name, label=str(path))
    return data


def write_json(path: Path, data: Any, schema_name: str) -> None:
    """Validate ``data`` against a named schema, then write it to ``path``."""
    validate_or_raise(data, schema_name, label=str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")

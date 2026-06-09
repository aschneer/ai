#!/usr/bin/env python3
"""Validate schedule and calendar YAML against JSON Schema.

Usage (from skills/schedule/):
    uv sync
    uv run schedule-validate <schedule-file>
    uv run python scripts/validate.py <schedule-file>
"""

from __future__ import annotations

from schedule_lib.validate_cli_lib import main

if __name__ == "__main__":
    raise SystemExit(main())

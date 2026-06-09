from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return normalize_for_schema(data)


def normalize_for_schema(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: normalize_for_schema(value) for key, value in data.items()}
    if isinstance(data, list):
        return [normalize_for_schema(value) for value in data]
    if isinstance(data, datetime):
        return data.date().isoformat()
    if isinstance(data, date):
        return data.isoformat()
    return data


def calendar_path_for_schedule(schedule_path: Path, schedule_data: dict[str, Any]) -> Path:
    calendar_ref = schedule_data.get("calendar", "calendar.yaml")
    return (schedule_path.parent / calendar_ref).resolve()

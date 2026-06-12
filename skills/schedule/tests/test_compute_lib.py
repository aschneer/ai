from datetime import date
from pathlib import Path

from schedule.compute_lib import compute_schedule
from schedule.io_lib import load_schedule_project, load_yaml

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "landscaping"
CALENDAR = {"weekends": ["sat", "sun"], "holidays": []}


def test_landscaping_schedule_dates() -> None:
    schedule_data = load_yaml(EXAMPLES / "schedule.yaml")
    calendar_data = load_yaml(EXAMPLES / "calendar.yaml")
    result = compute_schedule(schedule_data, calendar_data)
    by_id = {item.id: item for item in result.items}

    assert by_id[0].start == date(2026, 6, 9)
    assert by_id[11].start == date(2026, 6, 9)
    assert by_id[11].finish == date(2026, 6, 10)
    assert by_id[13].start == date(2026, 6, 22)
    assert by_id[14].start == date(2026, 6, 22)
    assert by_id[14].finish == date(2026, 6, 24)
    assert by_id[10].finish == date(2026, 6, 24)
    assert by_id[20].start == date(2026, 6, 24)
    assert by_id[20].finish == date(2026, 6, 29)
    assert result.project_finish == date(2026, 6, 29)


def test_nested_groups_schedule() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "group",
                "id": 10,
                "name": "Outer",
                "predecessors": ["0FS"],
                "children": [
                    {
                        "kind": "group",
                        "id": 11,
                        "name": "Inner",
                        "predecessors": ["10SS"],
                        "children": [
                            {
                                "kind": "task",
                                "id": 12,
                                "name": "Work",
                                "duration": "2d",
                                "predecessors": ["11SS"],
                            }
                        ],
                    }
                ],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[12].start == date(2026, 6, 9)
    assert by_id[12].finish == date(2026, 6, 10)
    assert by_id[11].start == date(2026, 6, 9)
    assert by_id[10].start == date(2026, 6, 9)


def test_finish_to_finish_link() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "First",
                "duration": "3d",
                "predecessors": ["0FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "Second",
                "duration": "2d",
                "predecessors": ["1FF"],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].finish == by_id[2].finish


def test_lag_delays_start() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "First",
                "duration": "1d",
                "predecessors": ["0FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "Second",
                "duration": "1d",
                "predecessors": ["1FS+3d"],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].finish == date(2026, 6, 9)
    assert by_id[2].start == date(2026, 6, 12)


def test_landscaping_loads_through_validation() -> None:
    project, errors = load_schedule_project(EXAMPLES / "schedule.yaml", require_calendar=True)

    assert errors == []
    assert project is not None

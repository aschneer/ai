from datetime import date
from pathlib import Path

from schedule.compute_lib import ComputedSchedule, computed_schedule_to_dict, compute_schedule
from schedule.io_lib import load_schedule_project, load_yaml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "home_renovation"
CALENDAR = {"weekends": ["sat", "sun"], "holidays": []}


def critical_ids(result: ComputedSchedule) -> set[int]:
    """Return IDs of items marked critical on a computed schedule."""
    return {item.id for item in result.items if item.is_critical}


def test_home_renovation_schedule_dates() -> None:
    schedule_data = load_yaml(FIXTURES / "schedule.yaml")
    calendar_data = load_yaml(FIXTURES / "calendar.yaml")
    result = compute_schedule(schedule_data, calendar_data)
    by_id = {item.id: item for item in result.items}

    assert by_id[0].start == date(2026, 6, 2)
    assert by_id[5].start == date(2026, 6, 16)
    assert by_id[11].start == date(2026, 6, 16)
    assert by_id[12].finish == date(2026, 6, 23)
    assert by_id[10].finish == date(2026, 6, 23)
    assert by_id[20].start == date(2026, 7, 1)
    assert by_id[42].start == date(2026, 8, 3)
    assert by_id[42].timing == "start_duration"
    assert by_id[52].duration == "3d"
    assert by_id[52].timing == "start_finish"
    assert by_id[60].finish == date(2026, 9, 4)
    assert by_id[60].timing == "finish_duration"
    assert result.project_finish == date(2026, 9, 10)
    assert critical_ids(result) == {70, 80}
    assert not by_id[42].is_critical


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
                                "timing": "auto",
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
                "timing": "auto",
                "duration": "3d",
                "predecessors": ["0FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "Second",
                "timing": "auto",
                "duration": "2d",
                "predecessors": ["1FF"],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].finish == by_id[2].finish
    assert critical_ids(result) == {0, 1, 2}


def test_lag_delays_start() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "First",
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["0FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "Second",
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["1FS+3d"],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].finish == date(2026, 6, 9)
    assert by_id[2].start == date(2026, 6, 12)
    assert critical_ids(result) == {0, 1, 2}


def test_computed_schedule_to_dict_marks_critical_items() -> None:
    schedule_data = load_yaml(FIXTURES / "schedule.yaml")
    calendar_data = load_yaml(FIXTURES / "calendar.yaml")
    result = compute_schedule(schedule_data, calendar_data)
    payload = computed_schedule_to_dict(result)

    assert payload["project_finish"] == "2026-09-10"
    assert "critical_path" not in payload
    by_id = {item["id"]: item for item in payload["items"]}
    assert by_id[80]["is_critical"] is True
    assert by_id[42]["is_critical"] is False
    assert by_id[80]["predecessors"] == [{"task_id": 70, "link_type": "FS", "lag": None}]
    assert by_id[43]["predecessors"] == [{"task_id": 42, "link_type": "FF", "lag": None}]
    assert by_id[0]["predecessors"] == []


def test_home_renovation_loads_through_validation() -> None:
    project, errors = load_schedule_project(FIXTURES / "schedule.yaml", require_calendar=True)

    assert errors == []
    assert project is not None


def test_start_duration_pins_start_and_computes_finish() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "First",
                "timing": "auto",
                "duration": "2d",
                "predecessors": ["0FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "Pinned",
                "timing": "start_duration",
                "start": "2026-06-12",
                "duration": "1d",
                "predecessors": ["1FS"],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[2].start == date(2026, 6, 12)
    assert by_id[2].finish == date(2026, 6, 12)


def test_finish_duration_pins_finish_and_computes_start() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "Pinned",
                "timing": "finish_duration",
                "finish": "2026-06-12",
                "duration": "2d",
                "predecessors": ["0FS"],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].finish == date(2026, 6, 12)
    assert by_id[1].start == date(2026, 6, 11)


def test_start_finish_derives_duration() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "Pinned span",
                "timing": "start_finish",
                "start": "2026-06-09",
                "finish": "2026-06-11",
                "predecessors": ["0FS"],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].start == date(2026, 6, 9)
    assert by_id[1].finish == date(2026, 6, 11)
    assert by_id[1].duration == "3d"

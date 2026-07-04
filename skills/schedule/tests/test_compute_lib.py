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
    assert by_id[12].finish == date(2026, 6, 24)
    assert by_id[10].finish == date(2026, 6, 24)
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


def test_computed_output_dict_contract() -> None:
    """Lock the JSON shape the Gantt viewer (gantt.js) consumes."""
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "Work",
                "timing": "auto",
                "duration": "2d",
                "predecessors": ["0FS+1d"],
            },
        ]
    }
    payload = computed_schedule_to_dict(compute_schedule(schedule_data, CALENDAR))

    assert set(payload) == {"items", "project_finish", "coverage"}
    assert payload["coverage"] == []
    item_keys = {
        "id",
        "kind",
        "name",
        "parent_id",
        "start",
        "finish",
        "working_days",
        "calendar_days",
        "timing",
        "duration",
        "milestone_date",
        "type",
        "is_critical",
        "predecessors",
    }
    for item in payload["items"]:
        assert set(item) == item_keys

    task = next(item for item in payload["items"] if item["id"] == 1)
    assert task["predecessors"] == [{"task_id": 0, "link_type": "FS", "lag": "+1d"}]
    assert task["working_days"] == 2
    assert task["calendar_days"] == 2

    milestone = next(item for item in payload["items"] if item["id"] == 0)
    assert milestone["working_days"] == 1
    assert milestone["calendar_days"] == 1


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


def test_fs_successor_starts_next_working_day() -> None:
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
                "predecessors": ["1FS"],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].start == date(2026, 6, 9)
    assert by_id[1].finish == date(2026, 6, 9)
    assert by_id[2].start == date(2026, 6, 10)
    assert by_id[2].finish == date(2026, 6, 10)


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


def test_pinned_task_without_predecessors_schedules_from_pin() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "Alex availability",
                "timing": "start_finish",
                "start": "2026-06-16",
                "finish": "2026-06-18",
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].start == date(2026, 6, 16)
    assert by_id[1].finish == date(2026, 6, 18)
    assert by_id[1].predecessors == []
    # Accepted edge: a no-pred floater that holds the max finish becomes the
    # lone critical terminal. See projects/260702_2018_optional_predecessors.
    assert by_id[1].is_critical


def test_group_without_predecessors_rolls_up_from_children() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "group",
                "id": 10,
                "name": "Availability",
                "children": [
                    {
                        "kind": "task",
                        "id": 11,
                        "name": "Alex",
                        "timing": "start_finish",
                        "start": "2026-06-16",
                        "finish": "2026-06-18",
                    },
                    {
                        "kind": "task",
                        "id": 12,
                        "name": "Sam",
                        "timing": "start_finish",
                        "start": "2026-06-10",
                        "finish": "2026-06-12",
                    },
                ],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[10].start == date(2026, 6, 10)
    assert by_id[10].finish == date(2026, 6, 18)


def test_group_predecessor_still_floors_children() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "group",
                "id": 10,
                "name": "Phase",
                "predecessors": ["0FS+5d"],
                "children": [
                    {
                        "kind": "task",
                        "id": 11,
                        "name": "Work",
                        "timing": "auto",
                        "duration": "2d",
                        "predecessors": ["10SS"],
                    },
                ],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[10].start == date(2026, 6, 16)
    assert by_id[11].start == date(2026, 6, 16)


def test_coverage_passes_through_without_affecting_finish() -> None:
    work = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "Work",
                "timing": "auto",
                "duration": "2d",
                "predecessors": ["0FS"],
            },
        ]
    }
    coverage = [
        {
            "name": "Maria",
            "segments": [{"start": "2026-12-01", "finish": "2026-12-20", "label": "Vacation"}],
        }
    ]
    without = computed_schedule_to_dict(compute_schedule(work, CALENDAR))
    with_coverage = computed_schedule_to_dict(
        compute_schedule({**work, "coverage": coverage}, CALENDAR)
    )

    # Far-future coverage must not push project finish, and must round-trip verbatim.
    assert with_coverage["project_finish"] == without["project_finish"]
    assert with_coverage["coverage"] == coverage
    assert without["coverage"] == []


def _deadline_schedule(deadline: str) -> dict:
    """A two-day task feeding a deadline milestone on the given date."""
    return {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "Work",
                "timing": "auto",
                "duration": "2d",
                "predecessors": ["0FS"],
            },
            {
                "kind": "milestone",
                "id": 9,
                "name": "Deadline",
                "date": deadline,
                "predecessors": ["1FS"],
            },
        ]
    }


def test_milestone_predecessor_does_not_move_milestone() -> None:
    # Task finishes 2026-06-10; the deadline stays on its authored date.
    result = compute_schedule(_deadline_schedule("2026-06-19"), CALENDAR)
    by_id = {item.id: item for item in result.items}

    assert by_id[1].finish == date(2026, 6, 10)
    assert by_id[9].start == date(2026, 6, 19)
    assert by_id[9].finish == date(2026, 6, 19)


def test_plain_deadline_milestone_is_not_critical() -> None:
    # A plain (non-designated) deadline milestone never marks its chain critical,
    # even at zero slack -- only a designated project_finish milestone does.
    result = compute_schedule(_deadline_schedule("2026-06-10"), CALENDAR)
    assert critical_ids(result) == {0, 1}


def _finish_milestone_schedule(deadline: str) -> dict:
    """A two-day task feeding a designated project_finish milestone."""
    schedule = _deadline_schedule(deadline)
    finish = next(item for item in schedule["items"] if item["id"] == 9)
    finish["type"] = "project_finish"
    return schedule


def test_project_finish_milestone_zero_slack_marks_chain_critical() -> None:
    # Feeder lands exactly on the finish date -> milestone and its chain critical.
    result = compute_schedule(_finish_milestone_schedule("2026-06-10"), CALENDAR)
    assert critical_ids(result) == {0, 1, 9}


def test_project_finish_milestone_with_buffer_empty_critical() -> None:
    # Feeder finishes 2026-06-10, finish milestone nine days later (buffer) ->
    # nothing critical, and project finish is the feeder's actual finish, not the date.
    result = compute_schedule(_finish_milestone_schedule("2026-06-19"), CALENDAR)
    assert critical_ids(result) == set()
    assert result.project_finish == date(2026, 6, 10)


def test_no_designated_finish_falls_back_to_longest_path() -> None:
    # Without a designated finish milestone, the computed latest finish drives it.
    result = compute_schedule(_deadline_schedule("2026-06-19"), CALENDAR)
    assert result.project_finish == date(2026, 6, 19)
    assert critical_ids(result) == set()


def test_milestone_predecessor_serialized() -> None:
    payload = computed_schedule_to_dict(
        compute_schedule(_deadline_schedule("2026-06-10"), CALENDAR)
    )
    milestone = next(item for item in payload["items"] if item["id"] == 9)
    assert milestone["predecessors"] == [
        {"task_id": 1, "link_type": "FS", "lag": None}
    ]

from schedule.logic_validate_lib import validate_schedule_logic

CALENDAR = {"weekends": ["sat", "sun"], "holidays": []}


def test_duplicate_id_error_per_pair() -> None:
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
                "id": 1,
                "name": "Duplicate",
                "duration": "1d",
                "predecessors": ["0FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert len(errors) == 1
    assert "duplicate id 1" in errors[0]
    assert "First" in errors[0]
    assert "Duplicate" in errors[0]


def test_unknown_predecessor_error() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "A",
                "duration": "1d",
                "predecessors": ["99FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("unknown task id" in error and "99" in error for error in errors)


def test_milestone_non_working_day_error() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "milestone",
                "id": 13,
                "name": "Weekend",
                "date": "2026-06-20",
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("milestone 13" in error and "non-working day" in error for error in errors)


def test_cyclic_dependency_error() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "A",
                "duration": "1d",
                "predecessors": ["2FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "B",
                "duration": "1d",
                "predecessors": ["1FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("cyclic predecessor dependency" in error for error in errors)


def test_top_level_must_not_mix_zero_with_other_predecessors() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "A",
                "duration": "1d",
                "predecessors": ["0FS", "2FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "B",
                "duration": "1d",
                "predecessors": ["0FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("must not include 0FS when other predecessors" in error for error in errors)


def test_child_must_not_reference_zero() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "group",
                "id": 10,
                "name": "Group",
                "predecessors": ["0FS"],
                "children": [
                    {
                        "kind": "task",
                        "id": 11,
                        "name": "Child",
                        "duration": "1d",
                        "predecessors": ["0FS"],
                    }
                ],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("child items must not reference id 0" in error for error in errors)


def test_invalid_predecessor_format_error() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "A",
                "duration": "1d",
                "predecessors": ["bad"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("invalid predecessor format" in error for error in errors)

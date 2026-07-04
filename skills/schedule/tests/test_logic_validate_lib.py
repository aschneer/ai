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
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["0FS"],
            },
            {
                "kind": "task",
                "id": 1,
                "name": "Duplicate",
                "timing": "auto",
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
                "timing": "auto",
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
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["2FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "B",
                "timing": "auto",
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
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["0FS", "2FS"],
            },
            {
                "kind": "task",
                "id": 2,
                "name": "B",
                "timing": "auto",
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
                        "timing": "auto",
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
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["bad"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("invalid predecessor format" in error for error in errors)


def test_start_duration_before_predecessor_is_error() -> None:
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
                "name": "Too early",
                "timing": "start_duration",
                "start": "2026-06-10",
                "duration": "1d",
                "predecessors": ["1FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("start_duration" in error and "earliest allowable start" in error for error in errors)


def test_start_finish_with_start_after_finish_is_error() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "Bad span",
                "timing": "start_finish",
                "start": "2026-06-12",
                "finish": "2026-06-10",
                "predecessors": ["0FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("start_finish" in error and "start" in error and "after finish" in error for error in errors)


def test_top_level_project_anchor_must_be_exactly_zero_fs() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "A",
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["0SS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("exactly [\"0FS\"]" in error for error in errors)


def test_child_with_only_parent_must_be_parent_ss() -> None:
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
                        "timing": "auto",
                        "duration": "1d",
                        "predecessors": ["10FS"],
                    }
                ],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("exactly [\"10SS\"]" in error for error in errors)


def test_child_with_specific_predecessor_is_allowed() -> None:
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
                        "timing": "auto",
                        "duration": "1d",
                        "predecessors": ["5FS"],
                    }
                ],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any("unknown task id" in error for error in errors)
    assert not any("exactly [\"10SS\"]" in error for error in errors)


def test_milestone_checks_require_calendar() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 1,
                "name": "A",
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["0FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, None)

    assert any("calendar file required for logic validation" in error for error in errors)


def test_milestone_unreachable_when_predecessor_chain_finishes_later() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 10,
                "name": "Long work",
                "timing": "auto",
                "duration": "2w",
                "predecessors": ["0FS"],
            },
            {
                "kind": "milestone",
                "id": 13,
                "name": "Permit approved",
                "date": "2026-06-15",
            },
            {
                "kind": "task",
                "id": 14,
                "name": "After permit",
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["10FS", "13FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any(
        "milestone 13" in error and "cannot be reached" in error and "2026-06-15" in error
        for error in errors
    )


def test_milestone_reachable_when_chain_finishes_before_milestone_date() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "task",
                "id": 10,
                "name": "Short work",
                "timing": "auto",
                "duration": "1w",
                "predecessors": ["0FS"],
            },
            {
                "kind": "milestone",
                "id": 13,
                "name": "Permit approved",
                "date": "2026-06-20",
            },
            {
                "kind": "task",
                "id": 14,
                "name": "After permit",
                "timing": "auto",
                "duration": "1d",
                "predecessors": ["10FS", "13FS"],
            },
        ]
    }

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert not any("cannot be reached" in error for error in errors)


def _deadline_items(deadline_pred: str, deadline: str = "2026-06-19") -> list:
    return [
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
            "predecessors": [deadline_pred],
        },
    ]


def test_milestone_deadline_missed_error() -> None:
    # Task finishes 2026-06-16; deadline on 2026-06-10 is unreachable.
    schedule_data = {"items": _deadline_items("1FS", deadline="2026-06-10")}
    schedule_data["items"][1]["duration"] = "5d"

    errors = validate_schedule_logic(schedule_data, CALENDAR)

    assert any(
        "milestone 9" in error and "missed" in error and "predecessor 1" in error
        for error in errors
    )


def test_milestone_predecessor_must_be_fs() -> None:
    errors = validate_schedule_logic({"items": _deadline_items("1SS")}, CALENDAR)
    assert any(
        "milestone 9" in error and "finish-to-start" in error for error in errors
    )


def test_milestone_predecessor_rejects_lag() -> None:
    errors = validate_schedule_logic({"items": _deadline_items("1FS+2d")}, CALENDAR)
    assert any(
        "milestone 9" in error and "finish-to-start" in error for error in errors
    )


def test_milestone_valid_fs_predecessor_passes() -> None:
    errors = validate_schedule_logic({"items": _deadline_items("1FS")}, CALENDAR)
    assert errors == []

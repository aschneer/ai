from pathlib import Path

from schedule.io_lib import load_yaml
from schedule.validate_lib import validate_calendar_file, validate_schedule_file

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "home_renovation"
DEMO = Path(__file__).resolve().parent.parent / "examples" / "farmers_market"


def test_home_renovation_fixture_passes_validation() -> None:
    schedule_path = FIXTURES / "schedule.yaml"
    calendar_path = FIXTURES / "calendar.yaml"

    schedule_data = load_yaml(schedule_path)
    calendar_data = load_yaml(calendar_path)

    assert isinstance(schedule_data, dict)
    assert isinstance(calendar_data, dict)
    assert validate_schedule_file(schedule_path, schedule_data) == []
    assert validate_calendar_file(calendar_path, calendar_data) == []


def test_farmers_market_demo_passes_validation() -> None:
    schedule_path = DEMO / "schedule.yaml"
    calendar_path = DEMO / "calendar.yaml"

    schedule_data = load_yaml(schedule_path)
    calendar_data = load_yaml(calendar_path)

    assert validate_schedule_file(schedule_path, schedule_data) == []
    assert validate_calendar_file(calendar_path, calendar_data) == []


def _schedule(*items: dict) -> dict:
    """Wrap items with a project-start milestone and calendar reference."""
    start = {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-05-04"}
    return {"calendar": "calendar.yaml", "items": [start, *items]}


def test_pinned_task_may_omit_predecessors() -> None:
    schedule = _schedule(
        {
            "kind": "task",
            "id": 5,
            "name": "Alex availability",
            "timing": "start_finish",
            "start": "2026-05-04",
            "finish": "2026-05-08",
        }
    )
    assert validate_schedule_file(Path("schedule.yaml"), schedule) == []


def test_pinned_task_may_have_empty_predecessors() -> None:
    schedule = _schedule(
        {
            "kind": "task",
            "id": 5,
            "name": "Alex availability",
            "timing": "start_duration",
            "start": "2026-05-04",
            "duration": "3d",
            "predecessors": [],
        }
    )
    assert validate_schedule_file(Path("schedule.yaml"), schedule) == []


def test_group_may_omit_predecessors() -> None:
    schedule = _schedule(
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
                    "start": "2026-05-04",
                    "finish": "2026-05-08",
                }
            ],
        }
    )
    assert validate_schedule_file(Path("schedule.yaml"), schedule) == []


def test_auto_task_still_requires_predecessors() -> None:
    schedule = _schedule(
        {
            "kind": "task",
            "id": 5,
            "name": "Work",
            "timing": "auto",
            "duration": "3d",
        }
    )
    errors = validate_schedule_file(Path("schedule.yaml"), schedule)
    assert errors, "auto task without predecessors must be rejected"


def test_farmers_market_full_demo_passes_validation() -> None:
    demo = Path(__file__).resolve().parent.parent / "examples" / "farmers_market_full"
    schedule_path = demo / "schedule.yaml"
    calendar_path = demo / "calendar.yaml"

    schedule_data = load_yaml(schedule_path)
    calendar_data = load_yaml(calendar_path)

    assert validate_schedule_file(schedule_path, schedule_data) == []
    assert validate_calendar_file(calendar_path, calendar_data) == []

from pathlib import Path

from schedule.io_lib import load_schedule_project

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "landscaping"


def test_load_schedule_project_with_calendar() -> None:
    project, errors = load_schedule_project(
        EXAMPLES / "schedule.yaml",
        require_calendar=True,
    )

    assert errors == []
    assert project is not None
    assert project.calendar_data is not None


def test_load_schedule_project_validate_without_require() -> None:
    project, errors = load_schedule_project(
        EXAMPLES / "schedule.yaml",
        require_calendar=False,
    )

    assert errors == []
    assert project is not None

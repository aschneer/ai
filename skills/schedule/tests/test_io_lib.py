from pathlib import Path

from schedule.io_lib import load_schedule_project

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "home_renovation"


def test_load_schedule_project_with_calendar() -> None:
    project, errors = load_schedule_project(
        FIXTURES / "schedule.yaml",
        require_calendar=True,
    )

    assert errors == []
    assert project is not None
    assert project.calendar_data is not None


def test_load_schedule_project_validate_without_require() -> None:
    project, errors = load_schedule_project(
        FIXTURES / "schedule.yaml",
        require_calendar=False,
    )

    assert errors == []
    assert project is not None

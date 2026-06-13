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


def test_farmers_market_full_demo_passes_validation() -> None:
    demo = Path(__file__).resolve().parent.parent / "examples" / "farmers_market_full"
    schedule_path = demo / "schedule.yaml"
    calendar_path = demo / "calendar.yaml"

    schedule_data = load_yaml(schedule_path)
    calendar_data = load_yaml(calendar_path)

    assert validate_schedule_file(schedule_path, schedule_data) == []
    assert validate_calendar_file(calendar_path, calendar_data) == []

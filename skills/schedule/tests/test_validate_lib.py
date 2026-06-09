from pathlib import Path

from schedule.io_lib import load_yaml
from schedule.validate_lib import validate_calendar_file, validate_schedule_file

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "landscaping"


def test_landscaping_example_passes_validation() -> None:
    schedule_path = EXAMPLES / "schedule.yaml"
    calendar_path = EXAMPLES / "calendar.yaml"

    schedule_data = load_yaml(schedule_path)
    calendar_data = load_yaml(calendar_path)

    assert isinstance(schedule_data, dict)
    assert isinstance(calendar_data, dict)
    assert validate_schedule_file(schedule_path, schedule_data) == []
    assert validate_calendar_file(calendar_path, calendar_data) == []

from datetime import date
from pathlib import Path

from schedule.compute_lib import compute_schedule
from schedule.io_lib import load_yaml

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "landscaping"


def test_landscaping_schedule_dates() -> None:
    schedule_data = load_yaml(EXAMPLES / "schedule.yaml")
    calendar_data = load_yaml(EXAMPLES / "calendar.yaml")
    result = compute_schedule(schedule_data, calendar_data)
    by_id = {item.id: item for item in result.items}

    assert by_id[0].start == date(2026, 6, 9)
    assert by_id[11].start == date(2026, 6, 9)
    assert by_id[11].finish == date(2026, 6, 10)
    assert by_id[13].start == date(2026, 6, 20)
    assert by_id[14].start == date(2026, 6, 22)
    assert by_id[14].finish == date(2026, 6, 24)
    assert by_id[10].finish == date(2026, 6, 24)
    assert by_id[20].start == date(2026, 6, 24)
    assert by_id[20].finish == date(2026, 6, 29)
    assert result.project_finish == date(2026, 6, 29)
    assert any(w.code == "milestone_non_working_day" and w.item_id == 13 for w in result.warnings)

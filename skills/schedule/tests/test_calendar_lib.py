from datetime import date

from schedule.calendar_lib import WorkingCalendar


def test_add_working_days_skips_weekend() -> None:
    calendar = WorkingCalendar.from_dict({"weekends": ["sat", "sun"], "holidays": []})
    assert calendar.add_working_days(date(2026, 6, 9), 1) == date(2026, 6, 10)
    assert calendar.task_finish(date(2026, 6, 9), "2d") == date(2026, 6, 10)


def test_task_finish_spans_holiday() -> None:
    calendar = WorkingCalendar.from_dict(
        {"weekends": ["sat", "sun"], "holidays": ["2026-06-10"]}
    )
    finish = calendar.task_finish(date(2026, 6, 9), "2d")
    assert finish == date(2026, 6, 11)


def test_count_working_days_inclusive() -> None:
    calendar = WorkingCalendar.from_dict({"weekends": ["sat", "sun"], "holidays": []})
    assert calendar.count_working_days(date(2026, 6, 9), date(2026, 6, 11)) == 3

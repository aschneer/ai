import pytest

from schedule.predecessors_lib import (
    LinkType,
    WORKING_DAYS_PER_WEEK,
    parse_duration_to_working_days,
    parse_predecessor,
)


def test_parse_predecessor_defaults_to_fs() -> None:
    link = parse_predecessor("5")
    assert link.task_id == 5
    assert link.link_type == LinkType.FS
    assert link.lag is None


def test_parse_predecessor_with_lag() -> None:
    link = parse_predecessor("7SS+2d")
    assert link.task_id == 7
    assert link.link_type == LinkType.SS
    assert link.lag == "+2d"


def test_parse_duration_days_and_weeks() -> None:
    assert parse_duration_to_working_days("4d") == 4
    assert parse_duration_to_working_days("2w") == 10
    assert parse_duration_to_working_days("-1d") == -1


def test_weeks_use_working_days_per_week_constant() -> None:
    assert parse_duration_to_working_days("2w") == 2 * WORKING_DAYS_PER_WEEK


def test_parse_predecessor_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_predecessor("bad")

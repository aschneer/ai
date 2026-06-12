"""Schedule computation warning codes and messages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WarningCode(str, Enum):
    """Machine-readable warning codes emitted by the scheduling engine."""

    UNKNOWN_PREDECESSOR = "unknown_predecessor"
    DUPLICATE_ITEM_ID = "duplicate_item_id"
    MILESTONE_NON_WORKING_DAY = "milestone_non_working_day"
    UNSCHEDULED_ITEM = "unscheduled_item"
    CONSTRAINT_NOT_MET = "constraint_not_met"
    MILESTONE_CONSTRAINT = "milestone_constraint"


@dataclass(frozen=True)
class ScheduleWarning:
    """Non-fatal schedule logic problem detected during computation."""

    code: WarningCode
    message: str
    item_id: int | None = None

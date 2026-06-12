"""CPM forward-pass scheduling for YAML schedule files.

Flattens nested schedule items, applies milestone dates, computes task and group
start/finish from predecessors and the working calendar, and emits warnings for
logic problems (R18).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from schedule.calendar_lib import WorkingCalendar
from schedule.kinds_lib import ItemKind
from schedule.predecessors_lib import (
    LinkType,
    PredecessorLink,
    parse_duration_to_working_days,
    parse_predecessors,
)
from schedule.warnings_lib import ScheduleWarning, WarningCode


@dataclass
class ScheduleItem:
    """One schedulable row from a schedule file, with computed dates filled in."""

    id: int
    kind: ItemKind
    name: str
    parent_id: int | None
    predecessors: list[PredecessorLink] = field(default_factory=list)
    duration: str | None = None
    milestone_date: date | None = None
    start: date | None = None
    finish: date | None = None

    @property
    def is_scheduled(self) -> bool:
        """True when both start and finish have been computed."""
        return self.start is not None and self.finish is not None


@dataclass
class ComputedSchedule:
    """Full result of a CPM forward pass."""

    items: list[ScheduleItem]
    project_finish: date | None
    warnings: list[ScheduleWarning]


def flatten_schedule_items(items: list[dict[str, Any]], parent_id: int | None = None) -> list[ScheduleItem]:
    """Walk nested YAML items and return a flat list with parent IDs attached."""
    flat: list[ScheduleItem] = []
    for raw in items:
        kind = ItemKind(raw["kind"])
        predecessors = parse_predecessors(raw.get("predecessors", [])) if kind != ItemKind.MILESTONE else []
        milestone_date = date.fromisoformat(raw["date"]) if kind == ItemKind.MILESTONE else None
        flat.append(
            ScheduleItem(
                id=raw["id"],
                kind=kind,
                name=raw["name"],
                parent_id=parent_id,
                predecessors=predecessors,
                duration=raw.get("duration"),
                milestone_date=milestone_date,
            )
        )
        if kind == ItemKind.GROUP:
            flat.extend(flatten_schedule_items(raw.get("children", []), raw["id"]))
    return flat


def compute_schedule(
    schedule_data: dict[str, Any],
    calendar_data: dict[str, Any],
) -> ComputedSchedule:
    """Run CPM forward-pass scheduling and return computed dates plus warnings."""
    calendar = WorkingCalendar.from_dict(calendar_data)
    items = flatten_schedule_items(schedule_data.get("items", []))
    by_id, warnings = _index_items(items)

    for item in items:
        for link in item.predecessors:
            if link.task_id not in by_id:
                warnings.append(
                    ScheduleWarning(
                        code=WarningCode.UNKNOWN_PREDECESSOR,
                        message=f"item {item.id} references unknown predecessor {link.task_id}",
                        item_id=item.id,
                    )
                )

    milestones = [item for item in items if item.kind == ItemKind.MILESTONE]
    for milestone in milestones:
        if milestone.milestone_date is None:
            continue
        milestone.start = milestone.milestone_date
        milestone.finish = milestone.milestone_date
        if not calendar.is_working_day(milestone.milestone_date):
            warnings.append(
                ScheduleWarning(
                    code=WarningCode.MILESTONE_NON_WORKING_DAY,
                    message=(
                        f"milestone {milestone.id} date {milestone.milestone_date} "
                        f"falls on a non-working day"
                    ),
                    item_id=milestone.id,
                )
            )

    tasks = [item for item in items if item.kind == ItemKind.TASK]
    groups = _groups_by_depth(items, by_id)

    for _ in range(len(items) + 1):
        changed = False
        for task in tasks:
            if _schedule_task(task, by_id, calendar):
                changed = True
        for group in groups:
            if _schedule_group(group, by_id, calendar):
                changed = True
        if not changed:
            break

    warnings.extend(_check_unscheduled_items(items))
    warnings.extend(_check_predecessor_constraints(items, by_id, calendar))
    warnings.extend(_check_milestone_warnings(items, by_id))

    scheduled = [item for item in items if item.is_scheduled]
    project_finish = max((item.finish for item in scheduled if item.finish is not None), default=None)
    return ComputedSchedule(items=items, project_finish=project_finish, warnings=warnings)


def computed_schedule_to_dict(result: ComputedSchedule) -> dict[str, Any]:
    """Serialize a computed schedule to JSON-friendly dicts."""
    return {
        "items": [
            {
                "id": item.id,
                "kind": item.kind.value,
                "name": item.name,
                "parent_id": item.parent_id,
                "start": item.start.isoformat() if item.start else None,
                "finish": item.finish.isoformat() if item.finish else None,
                "duration": item.duration,
                "milestone_date": item.milestone_date.isoformat() if item.milestone_date else None,
            }
            for item in result.items
        ],
        "project_finish": result.project_finish.isoformat() if result.project_finish else None,
        "warnings": [
            {"code": warning.code.value, "message": warning.message, "item_id": warning.item_id}
            for warning in result.warnings
        ],
    }


def _index_items(items: list[ScheduleItem]) -> tuple[dict[int, ScheduleItem], list[ScheduleWarning]]:
    """Build id index and warn on duplicate IDs (last occurrence wins)."""
    by_id: dict[int, ScheduleItem] = {}
    warnings: list[ScheduleWarning] = []
    for item in items:
        if item.id in by_id:
            warnings.append(
                ScheduleWarning(
                    code=WarningCode.DUPLICATE_ITEM_ID,
                    message=f"duplicate item id {item.id}: {by_id[item.id].name!r} and {item.name!r}",
                    item_id=item.id,
                )
            )
        by_id[item.id] = item
    return by_id, warnings


def _groups_by_depth(items: list[ScheduleItem], by_id: dict[int, ScheduleItem]) -> list[ScheduleItem]:
    """Return groups deepest-first so nested rollups schedule correctly."""

    def depth(item: ScheduleItem) -> int:
        level = 0
        parent_id = item.parent_id
        while parent_id is not None:
            level += 1
            parent = by_id.get(parent_id)
            if parent is None:
                break
            parent_id = parent.parent_id
        return level

    groups = [item for item in items if item.kind == ItemKind.GROUP]
    return sorted(groups, key=depth, reverse=True)


def _schedule_task(
    task: ScheduleItem,
    by_id: dict[int, ScheduleItem],
    calendar: WorkingCalendar,
) -> bool:
    """Compute start/finish for one task. Returns True if dates changed."""
    if task.duration is None:
        return False

    parent = by_id.get(task.parent_id) if task.parent_id is not None else None
    earliest = _minimum_start_from_predecessors(task, by_id, calendar, task.duration)
    parent_floor = _parent_earliest_start(parent, by_id, calendar) if parent else None
    if parent_floor is not None:
        earliest = max(earliest, parent_floor) if earliest is not None else parent_floor
    if earliest is None:
        return False

    finish = calendar.task_finish(earliest, task.duration)
    if task.start == earliest and task.finish == finish:
        return False
    task.start = earliest
    task.finish = finish
    return True


def _schedule_group(
    group: ScheduleItem,
    by_id: dict[int, ScheduleItem],
    calendar: WorkingCalendar,
) -> bool:
    """Roll up group dates from children and predecessor constraints. Returns True if dates changed."""
    children = [item for item in by_id.values() if item.parent_id == group.id]
    if not children or not all(child.is_scheduled for child in children):
        return False

    child_start = min(child.start for child in children if child.start is not None)
    child_finish = max(child.finish for child in children if child.finish is not None)
    pred_start = _minimum_start_from_predecessors(group, by_id, calendar, duration="1d")
    start = child_start if pred_start is None else max(pred_start, child_start)
    finish = child_finish

    if group.start == start and group.finish == finish:
        return False
    group.start = start
    group.finish = finish
    return True


def _parent_earliest_start(
    parent: ScheduleItem,
    by_id: dict[int, ScheduleItem],
    calendar: WorkingCalendar,
) -> date | None:
    """Earliest start allowed for children under a parent (R2)."""
    if parent.start is not None:
        return parent.start
    if parent.kind == ItemKind.GROUP:
        return _group_anchor_start(parent, by_id, calendar)
    return None


def _group_anchor_start(
    group: ScheduleItem,
    by_id: dict[int, ScheduleItem],
    calendar: WorkingCalendar,
) -> date | None:
    """Group start from predecessors only, before children are rolled up."""
    if group.start is not None:
        return group.start
    return _minimum_start_from_predecessors(group, by_id, calendar, "1d")


def _minimum_start_from_predecessors(
    item: ScheduleItem,
    by_id: dict[int, ScheduleItem],
    calendar: WorkingCalendar,
    duration: str,
) -> date | None:
    """Latest minimum start date implied by all predecessor links."""
    if not item.predecessors:
        return None

    candidates: list[date] = []
    for link in item.predecessors:
        pred = by_id.get(link.task_id)
        if pred is None:
            return None
        candidate = _constraint_start(link, pred, duration, calendar, by_id)
        if candidate is None:
            return None
        candidates.append(candidate)

    return max(candidates)


def _pred_anchors(
    pred: ScheduleItem,
    by_id: dict[int, ScheduleItem],
    calendar: WorkingCalendar,
) -> tuple[date | None, date | None]:
    """Start/finish anchors available from a predecessor for the given link type."""
    if pred.kind == ItemKind.MILESTONE:
        if pred.start is None:
            return None, None
        return pred.start, pred.start
    if pred.is_scheduled:
        return pred.start, pred.finish
    if pred.kind == ItemKind.GROUP:
        # Finish is unknown until children roll up; FS/FF wait on finish, SS/SF use anchor start.
        return _group_anchor_start(pred, by_id, calendar), None
    return None, None


def _constraint_start(
    link: PredecessorLink,
    pred: ScheduleItem,
    duration: str,
    calendar: WorkingCalendar,
    by_id: dict[int, ScheduleItem],
) -> date | None:
    """Earliest allowed start for a successor given one predecessor link."""
    anchor_start, anchor_finish = _pred_anchors(pred, by_id, calendar)

    if link.link_type == LinkType.FS:
        if anchor_finish is None:
            return None
        anchor = calendar.apply_lag(anchor_finish, link.lag)
        return calendar.normalize_to_working_day(anchor)
    if link.link_type == LinkType.SS:
        if anchor_start is None:
            return None
        anchor = calendar.apply_lag(anchor_start, link.lag)
        return calendar.normalize_to_working_day(anchor)
    if link.link_type == LinkType.FF:
        if anchor_finish is None:
            return None
        required_finish = calendar.apply_lag(anchor_finish, link.lag)
        return _start_for_finish(required_finish, duration, calendar)
    if link.link_type == LinkType.SF:
        if anchor_start is None:
            return None
        required_finish = calendar.apply_lag(anchor_start, link.lag)
        return _start_for_finish(required_finish, duration, calendar)
    return None


def _start_for_finish(required_finish: date, duration: str, calendar: WorkingCalendar) -> date:
    """Back-calculate task start so it finishes on required_finish."""
    working_days = max(parse_duration_to_working_days(duration), 1)
    return calendar.add_working_days(required_finish, -(working_days - 1))


def _check_unscheduled_items(items: list[ScheduleItem]) -> list[ScheduleWarning]:
    """Warn when tasks or groups could not be scheduled."""
    warnings: list[ScheduleWarning] = []
    for item in items:
        if item.kind == ItemKind.MILESTONE or item.is_scheduled:
            continue
        warnings.append(
            ScheduleWarning(
                code=WarningCode.UNSCHEDULED_ITEM,
                message=f"item {item.id} ({item.kind.value}) could not be scheduled",
                item_id=item.id,
            )
        )
    return warnings


def _check_predecessor_constraints(
    items: list[ScheduleItem],
    by_id: dict[int, ScheduleItem],
    calendar: WorkingCalendar,
) -> list[ScheduleWarning]:
    """Verify computed dates satisfy all predecessor links."""
    warnings: list[ScheduleWarning] = []
    for item in items:
        if item.kind == ItemKind.MILESTONE or not item.is_scheduled:
            continue
        duration = item.duration or "1d"
        for link in item.predecessors:
            pred = by_id.get(link.task_id)
            if pred is None or not pred.is_scheduled or item.start is None:
                continue
            required_start = _constraint_start(link, pred, duration, calendar, by_id)
            if required_start is None:
                continue
            if item.start < required_start:
                warnings.append(
                    ScheduleWarning(
                        code=WarningCode.CONSTRAINT_NOT_MET,
                        message=(
                            f"item {item.id} starts {item.start} but predecessor "
                            f"{link.task_id}{link.link_type.value} requires {required_start}"
                        ),
                        item_id=item.id,
                    )
                )
    return warnings


def _check_milestone_warnings(items: list[ScheduleItem], by_id: dict[int, ScheduleItem]) -> list[ScheduleWarning]:
    """Emit R18 warnings when computed dates conflict with milestone constraints."""
    warnings: list[ScheduleWarning] = []
    for item in items:
        if not item.is_scheduled or item.kind != ItemKind.TASK:
            continue
        for link in item.predecessors:
            pred = by_id.get(link.task_id)
            if pred is None or pred.kind != ItemKind.MILESTONE or pred.start is None:
                continue
            if link.link_type in {LinkType.FF, LinkType.SF} and item.finish and item.finish < pred.start:
                warnings.append(
                    ScheduleWarning(
                        code=WarningCode.MILESTONE_CONSTRAINT,
                        message=(
                            f"task {item.id} finishes {item.finish} before milestone "
                            f"{pred.id} date {pred.start} via {link.task_id}{link.link_type.value}"
                        ),
                        item_id=item.id,
                    )
                )
            if link.link_type in {LinkType.FS, LinkType.SS} and item.start and item.start < pred.start:
                warnings.append(
                    ScheduleWarning(
                        code=WarningCode.MILESTONE_CONSTRAINT,
                        message=(
                            f"task {item.id} starts {item.start} before milestone "
                            f"{pred.id} date {pred.start} via {link.task_id}{link.link_type.value}"
                        ),
                        item_id=item.id,
                    )
                )
    return warnings

"""CPM forward-pass scheduling for YAML schedule files.

Expects validated input — run ``logic_validate_lib.validate_schedule_logic`` first.
Algorithm overview: ``references/scheduling_algorithm.md``.
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
    is_critical: bool = False

    @property
    def is_scheduled(self) -> bool:
        """True when both start and finish have been computed."""
        return self.start is not None and self.finish is not None


@dataclass
class ComputedSchedule:
    """Full result of a CPM forward pass."""

    items: list[ScheduleItem]
    project_finish: date | None


@dataclass
class SchedulingContext:
    """Shared state for one CPM forward pass."""

    calendar: WorkingCalendar
    items: list[ScheduleItem]
    by_id: dict[int, ScheduleItem]
    tasks: list[ScheduleItem]
    groups: list[ScheduleItem]
    milestones: list[ScheduleItem]


def flatten_schedule_items(items: list[dict[str, Any]], parent_id: int | None = None) -> list[ScheduleItem]:
    """Walk nested YAML items and return a flat list with parent IDs attached."""
    flat: list[ScheduleItem] = []
    for raw in items:
        item = _schedule_item_from_raw(raw, parent_id)
        flat.append(item)
        if item.kind == ItemKind.GROUP:
            flat.extend(flatten_schedule_items(raw.get("children", []), item.id))
    return flat


def compute_schedule(
    schedule_data: dict[str, Any],
    calendar_data: dict[str, Any],
) -> ComputedSchedule:
    """Run CPM forward-pass scheduling and return computed dates."""
    # Flatten nested items, index by ID, and partition tasks, groups, and milestones.
    ctx = _build_scheduling_context(schedule_data, calendar_data)

    # Copy milestone dates to start/finish.
    _apply_milestone_dates(ctx)

    # Iteratively schedule tasks and roll up groups until dates stop changing.
    _run_until_fixed_point(ctx)

    project_finish = _project_finish(ctx.items)
    _mark_critical_items(ctx, project_finish)

    return ComputedSchedule(
        items=ctx.items,
        project_finish=project_finish,
    )


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
                "is_critical": item.is_critical,
            }
            for item in result.items
        ],
        "project_finish": result.project_finish.isoformat() if result.project_finish else None,
    }


def _schedule_item_from_raw(raw: dict[str, Any], parent_id: int | None) -> ScheduleItem:
    """Build one ScheduleItem from a YAML item dict."""
    kind = ItemKind(raw["kind"])
    predecessors = parse_predecessors(raw.get("predecessors", [])) if kind != ItemKind.MILESTONE else []
    milestone_date = date.fromisoformat(raw["date"]) if kind == ItemKind.MILESTONE else None
    return ScheduleItem(
        id=raw["id"],
        kind=kind,
        name=raw["name"],
        parent_id=parent_id,
        predecessors=predecessors,
        duration=raw.get("duration"),
        milestone_date=milestone_date,
    )


def _build_scheduling_context(
    schedule_data: dict[str, Any],
    calendar_data: dict[str, Any],
) -> SchedulingContext:
    """Parse schedule data and build shared scheduling state."""
    calendar = WorkingCalendar.from_dict(calendar_data)
    items = flatten_schedule_items(schedule_data.get("items", []))
    by_id = _index_items(items)
    return SchedulingContext(
        calendar=calendar,
        items=items,
        by_id=by_id,
        tasks=[item for item in items if item.kind == ItemKind.TASK],
        groups=_groups_by_depth(items, by_id),
        milestones=[item for item in items if item.kind == ItemKind.MILESTONE],
    )


def _apply_milestone_dates(ctx: SchedulingContext) -> None:
    """Set milestone start/finish from authoritative dates."""
    for milestone in ctx.milestones:
        if milestone.milestone_date is None:
            continue
        milestone.start = milestone.milestone_date
        milestone.finish = milestone.milestone_date


def _run_until_fixed_point(ctx: SchedulingContext) -> None:
    """Schedule tasks and roll up groups until no dates change."""
    for _ in range(len(ctx.items) + 1):
        changed = False
        for task in ctx.tasks:
            if _schedule_task(task, ctx):
                changed = True
        for group in ctx.groups:
            if _schedule_group(group, ctx):
                changed = True
        if not changed:
            break


def _project_finish(items: list[ScheduleItem]) -> date | None:
    """Return the latest finish date among scheduled items."""
    scheduled = [item for item in items if item.is_scheduled]
    return max((item.finish for item in scheduled if item.finish is not None), default=None)


def _index_items(items: list[ScheduleItem]) -> dict[int, ScheduleItem]:
    """Build id index (IDs are unique — enforced by logic validation)."""
    return {item.id: item for item in items}


def _item_depth(item: ScheduleItem, by_id: dict[int, ScheduleItem]) -> int:
    """Count nesting levels from item to the top level."""
    level = 0
    parent_id = item.parent_id
    while parent_id is not None:
        level += 1
        parent = by_id.get(parent_id)
        if parent is None:
            break
        parent_id = parent.parent_id
    return level


def _groups_by_depth(items: list[ScheduleItem], by_id: dict[int, ScheduleItem]) -> list[ScheduleItem]:
    """Return groups deepest-first so nested rollups schedule correctly."""
    groups = [item for item in items if item.kind == ItemKind.GROUP]
    return sorted(groups, key=lambda item: _item_depth(item, by_id), reverse=True)


def _schedule_task(task: ScheduleItem, ctx: SchedulingContext) -> bool:
    """Compute start/finish for one task. Returns True if dates changed."""
    if task.duration is None:
        return False

    parent = ctx.by_id.get(task.parent_id) if task.parent_id is not None else None
    earliest = _minimum_start_from_predecessors(task, ctx, task.duration)
    parent_floor = _parent_earliest_start(parent, ctx) if parent else None
    if parent_floor is not None:
        earliest = max(earliest, parent_floor) if earliest is not None else parent_floor
    if earliest is None:
        return False

    finish = ctx.calendar.task_finish(earliest, task.duration)
    if task.start == earliest and task.finish == finish:
        return False
    task.start = earliest
    task.finish = finish
    return True


def _schedule_group(group: ScheduleItem, ctx: SchedulingContext) -> bool:
    """Roll up group dates from children and predecessor constraints. Returns True if dates changed."""
    children = [item for item in ctx.by_id.values() if item.parent_id == group.id]
    if not children or not all(child.is_scheduled for child in children):
        return False

    child_start = min(child.start for child in children if child.start is not None)
    child_finish = max(child.finish for child in children if child.finish is not None)
    pred_start = _minimum_start_from_predecessors(group, ctx, duration="1d")
    start = child_start if pred_start is None else max(pred_start, child_start)
    finish = child_finish

    if group.start == start and group.finish == finish:
        return False
    group.start = start
    group.finish = finish
    return True


def _parent_earliest_start(parent: ScheduleItem, ctx: SchedulingContext) -> date | None:
    """Earliest start allowed for children under a parent (R2)."""
    if parent.start is not None:
        return parent.start
    if parent.kind == ItemKind.GROUP:
        return _group_anchor_start(parent, ctx)
    return None


def _group_anchor_start(group: ScheduleItem, ctx: SchedulingContext) -> date | None:
    """Group start from predecessors only, before children are rolled up."""
    if group.start is not None:
        return group.start
    return _minimum_start_from_predecessors(group, ctx, "1d")


def _minimum_start_from_predecessors(
    item: ScheduleItem,
    ctx: SchedulingContext,
    duration: str,
) -> date | None:
    """Latest minimum start date implied by all predecessor links."""
    if not item.predecessors:
        return None

    candidates: list[date] = []
    for link in item.predecessors:
        pred = ctx.by_id.get(link.task_id)
        if pred is None:
            return None
        candidate = _constraint_start(link, pred, duration, ctx)
        if candidate is None:
            return None
        candidates.append(candidate)

    return max(candidates)


def _pred_anchors(
    pred: ScheduleItem,
    ctx: SchedulingContext,
) -> tuple[date | None, date | None]:
    """Start/finish anchors available from a predecessor for the given link type."""
    if pred.kind == ItemKind.MILESTONE:
        if pred.start is None:
            return None, None
        return pred.start, pred.start
    if pred.is_scheduled:
        return pred.start, pred.finish
    if pred.kind == ItemKind.GROUP:
        return _group_anchor_start(pred, ctx), None
    return None, None


def _constraint_start(
    link: PredecessorLink,
    pred: ScheduleItem,
    duration: str,
    ctx: SchedulingContext,
) -> date | None:
    """Earliest allowed start for a successor given one predecessor link."""
    anchor_start, anchor_finish = _pred_anchors(pred, ctx)

    if link.link_type == LinkType.FS:
        return _fs_constraint_start(anchor_finish, link.lag, ctx.calendar)
    if link.link_type == LinkType.SS:
        return _ss_constraint_start(anchor_start, link.lag, ctx.calendar)
    if link.link_type == LinkType.FF:
        return _ff_constraint_start(anchor_finish, link.lag, duration, ctx.calendar)
    if link.link_type == LinkType.SF:
        return _sf_constraint_start(anchor_start, link.lag, duration, ctx.calendar)
    return None


def _fs_constraint_start(
    anchor_finish: date | None,
    lag: str | None,
    calendar: WorkingCalendar,
) -> date | None:
    """Finish-to-start: successor starts after predecessor finishes."""
    if anchor_finish is None:
        return None
    anchor = calendar.apply_lag(anchor_finish, lag)
    return calendar.normalize_to_working_day(anchor)


def _ss_constraint_start(
    anchor_start: date | None,
    lag: str | None,
    calendar: WorkingCalendar,
) -> date | None:
    """Start-to-start: successor starts when predecessor starts."""
    if anchor_start is None:
        return None
    anchor = calendar.apply_lag(anchor_start, lag)
    return calendar.normalize_to_working_day(anchor)


def _ff_constraint_start(
    anchor_finish: date | None,
    lag: str | None,
    duration: str,
    calendar: WorkingCalendar,
) -> date | None:
    """Finish-to-finish: back-calculate start so both finish together."""
    if anchor_finish is None:
        return None
    required_finish = calendar.apply_lag(anchor_finish, lag)
    return _start_for_finish(required_finish, duration, calendar)


def _sf_constraint_start(
    anchor_start: date | None,
    lag: str | None,
    duration: str,
    calendar: WorkingCalendar,
) -> date | None:
    """Start-to-finish: back-calculate start from predecessor start."""
    if anchor_start is None:
        return None
    required_finish = calendar.apply_lag(anchor_start, lag)
    return _start_for_finish(required_finish, duration, calendar)


def _start_for_finish(required_finish: date, duration: str, calendar: WorkingCalendar) -> date:
    """Back-calculate task start so it finishes on required_finish."""
    working_days = max(parse_duration_to_working_days(duration), 1)
    return calendar.add_working_days(required_finish, -(working_days - 1))


def _mark_critical_items(ctx: SchedulingContext, project_finish: date | None) -> None:
    """Set ``is_critical`` on items that drive project finish."""
    critical_ids = _compute_critical_item_ids(ctx, project_finish)
    for item in ctx.items:
        item.is_critical = item.id in critical_ids


def _compute_critical_item_ids(
    ctx: SchedulingContext,
    project_finish: date | None,
) -> frozenset[int]:
    """Return IDs on the chain that sets project finish."""
    if project_finish is None:
        return frozenset()

    critical_ids: set[int] = set()
    for terminal in _critical_terminal_items(ctx, project_finish):
        _collect_critical_chain(terminal, ctx, set(), critical_ids)
    return frozenset(critical_ids)


def _critical_terminal_items(
    ctx: SchedulingContext,
    project_finish: date,
) -> list[ScheduleItem]:
    """Tasks (preferably) whose finish equals project finish."""
    terminals = [
        item
        for item in ctx.items
        if item.is_scheduled and item.finish == project_finish and item.kind == ItemKind.TASK
    ]
    if terminals:
        return terminals
    return [item for item in ctx.items if item.is_scheduled and item.finish == project_finish]


def _collect_critical_chain(
    item: ScheduleItem,
    ctx: SchedulingContext,
    visiting: set[int],
    critical_ids: set[int],
) -> None:
    """Walk backward from ``item``, adding driving predecessors to ``critical_ids``."""
    if item.id in visiting:
        return
    visiting.add(item.id)
    critical_ids.add(item.id)
    for pred_id in _driving_predecessor_ids(item, ctx):
        pred = ctx.by_id.get(pred_id)
        if pred is not None:
            _collect_critical_chain(pred, ctx, visiting, critical_ids)


def _driving_predecessor_ids(item: ScheduleItem, ctx: SchedulingContext) -> list[int]:
    """Return predecessors that actually set this item's scheduled dates.

    Uses driving predecessor links (constraint equals actual start) and
    rollup-driving children, rather than full total-float math — enough to
    highlight the chain that determines project finish in the Gantt viewer.
    """
    by_id = ctx.by_id
    ids: list[int] = []

    if item.predecessors and item.start is not None:
        duration = item.duration or "1d"
        constraints: list[tuple[int, date]] = []
        for link in item.predecessors:
            pred = by_id.get(link.task_id)
            if pred is None:
                continue
            candidate = _constraint_start(link, pred, duration, ctx)
            if candidate is not None:
                constraints.append((pred.id, candidate))
        if constraints:
            latest = max(candidate for _, candidate in constraints)
            ids.extend(pred_id for pred_id, candidate in constraints if candidate == latest)

    if item.kind == ItemKind.GROUP and item.finish is not None:
        children = [
            child
            for child in ctx.items
            if child.parent_id == item.id and child.is_scheduled and child.finish is not None
        ]
        if children:
            latest_finish = max(child.finish for child in children)
            if latest_finish == item.finish:
                ids.extend(child.id for child in children if child.finish == latest_finish)

    seen: set[int] = set()
    unique: list[int] = []
    for pred_id in ids:
        if pred_id not in seen:
            seen.add(pred_id)
            unique.append(pred_id)
    return unique

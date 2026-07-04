"""CPM forward-pass scheduling for YAML schedule files.

Expects validated input — run ``logic_validate_lib.validate_schedule_logic`` first.
Algorithm overview: ``context/scheduling_algorithm.md``.
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
    timing: str = "auto"
    duration: str | None = None
    pinned_start: date | None = None
    pinned_finish: date | None = None
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
    coverage: list[dict[str, Any]]
    calendar: WorkingCalendar


@dataclass
class SchedulingContext:
    """Shared state for one CPM forward pass."""

    calendar: WorkingCalendar
    items: list[ScheduleItem]
    by_id: dict[int, ScheduleItem]
    tasks: list[ScheduleItem]
    groups: list[ScheduleItem]
    milestones: list[ScheduleItem]
    auto_only: bool = False


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
        coverage=schedule_data.get("coverage", []),
        calendar=ctx.calendar,
    )


def computed_schedule_to_dict(result: ComputedSchedule) -> dict[str, Any]:
    """Serialize a computed schedule to JSON-friendly dicts."""

    def span_days(item: ScheduleItem) -> tuple[int | None, int | None]:
        """Working and calendar day counts for a placed item; None if unplaced."""
        if not item.start or not item.finish:
            return None, None
        working = result.calendar.count_working_days(item.start, item.finish)
        calendar_days = (item.finish - item.start).days + 1
        return working, calendar_days

    def item_dict(item: ScheduleItem) -> dict[str, Any]:
        working, calendar_days = span_days(item)
        return {
            "id": item.id,
            "kind": item.kind.value,
            "name": item.name,
            "parent_id": item.parent_id,
            "start": item.start.isoformat() if item.start else None,
            "finish": item.finish.isoformat() if item.finish else None,
            "working_days": working,
            "calendar_days": calendar_days,
            "timing": item.timing if item.kind == ItemKind.TASK else None,
            "duration": item.duration,
            "milestone_date": item.milestone_date.isoformat() if item.milestone_date else None,
            "is_critical": item.is_critical,
            "predecessors": [
                {
                    "task_id": link.task_id,
                    "link_type": link.link_type.value,
                    "lag": link.lag,
                }
                for link in item.predecessors
            ],
        }

    return {
        "items": [item_dict(item) for item in result.items],
        "project_finish": result.project_finish.isoformat() if result.project_finish else None,
        "coverage": result.coverage,
    }


def validate_pinned_task_bounds(
    schedule_data: dict[str, Any],
    calendar_data: dict[str, Any],
) -> list[str]:
    """Return logic errors for pinned tasks that violate predecessor or parent bounds."""
    ctx = _validation_scheduling_context(schedule_data, calendar_data, auto_only=True)

    errors: list[str] = []
    for task in ctx.tasks:
        if task.timing == "auto":
            continue
        errors.extend(_pinned_task_bound_errors(task, ctx))
    return errors


def validate_milestone_reachability(
    schedule_data: dict[str, Any],
    calendar_data: dict[str, Any],
) -> list[str]:
    """Return logic errors when predecessor chains finish after a milestone they must reach (R18).

    When item S lists milestone M among its predecessors, every other transitive predecessor
    of S must finish on or before M's authoritative date. Otherwise M's date is unreachable.
    """
    ctx = _validation_scheduling_context(schedule_data, calendar_data)

    errors: list[str] = []
    for milestone in ctx.milestones:
        if milestone.id == 0 or milestone.milestone_date is None:
            continue

        errors.extend(_milestone_deadline_errors(milestone, ctx))

        violation = _worst_upstream_finish_for_milestone(milestone, ctx)
        if violation is None:
            continue

        worst_finish, worst_item_id = violation
        if worst_finish <= milestone.milestone_date:
            continue

        errors.append(
            f"schedule: milestone {milestone.id}: date {milestone.milestone_date} "
            f"cannot be reached — predecessor chain for item {worst_item_id} "
            f"finishes {worst_finish}"
        )

    return errors


def _milestone_deadline_errors(
    milestone: ScheduleItem,
    ctx: SchedulingContext,
) -> list[str]:
    """A milestone's own predecessors must finish on or before its deadline date.

    Milestone predecessors are annotation only (the date is fixed), so if the
    feeding chain finishes after the date, the deadline is missed — a hard error.
    """
    errors: list[str] = []
    for link in milestone.predecessors:
        pred = ctx.by_id.get(link.task_id)
        if pred is None or pred.finish is None:
            continue
        if pred.finish > milestone.milestone_date:
            errors.append(
                f"schedule: milestone {milestone.id}: deadline {milestone.milestone_date} "
                f"missed — predecessor {link.task_id} finishes {pred.finish}"
            )
    return errors


def _validation_scheduling_context(
    schedule_data: dict[str, Any],
    calendar_data: dict[str, Any],
    *,
    auto_only: bool = False,
) -> SchedulingContext:
    """Build scheduling context and run forward pass for validation helpers."""
    ctx = _build_scheduling_context(schedule_data, calendar_data)
    ctx.auto_only = auto_only
    _apply_milestone_dates(ctx)
    _run_until_fixed_point(ctx)
    return ctx


def _worst_upstream_finish_for_milestone(
    milestone: ScheduleItem,
    ctx: SchedulingContext,
) -> tuple[date, int] | None:
    """Return the latest upstream finish and the dependent item that exposes it."""
    worst_finish: date | None = None
    worst_item_id: int | None = None

    for item in ctx.items:
        if item.kind == ItemKind.MILESTONE:
            continue
        if not any(link.task_id == milestone.id for link in item.predecessors):
            continue

        upstream_ids = _collect_upstream_predecessor_ids(item, milestone.id, ctx.by_id)
        for upstream_id in upstream_ids:
            upstream = ctx.by_id.get(upstream_id)
            if upstream is None or not upstream.is_scheduled or upstream.finish is None:
                continue
            if worst_finish is None or upstream.finish > worst_finish:
                worst_finish = upstream.finish
                worst_item_id = item.id

    if worst_finish is None or worst_item_id is None:
        return None
    return worst_finish, worst_item_id


def _collect_upstream_predecessor_ids(
    item: ScheduleItem,
    exclude_id: int,
    by_id: dict[int, ScheduleItem],
) -> set[int]:
    """Transitive predecessor IDs for item, excluding exclude_id and not walking through milestones."""
    seen: set[int] = set()
    stack = [link.task_id for link in item.predecessors if link.task_id != exclude_id]

    while stack:
        pred_id = stack.pop()
        if pred_id in seen:
            continue
        seen.add(pred_id)
        pred = by_id.get(pred_id)
        if pred is None or pred.kind == ItemKind.MILESTONE:
            continue
        for link in pred.predecessors:
            if link.task_id not in seen:
                stack.append(link.task_id)

    return seen


def _schedule_item_from_raw(raw: dict[str, Any], parent_id: int | None) -> ScheduleItem:
    """Build one ScheduleItem from a YAML item dict."""
    kind = ItemKind(raw["kind"])
    predecessors = parse_predecessors(raw.get("predecessors", []))
    milestone_date = date.fromisoformat(raw["date"]) if kind == ItemKind.MILESTONE else None
    timing = raw.get("timing", "auto") if kind == ItemKind.TASK else "auto"
    pinned_start = date.fromisoformat(raw["start"]) if kind == ItemKind.TASK and "start" in raw else None
    pinned_finish = date.fromisoformat(raw["finish"]) if kind == ItemKind.TASK and "finish" in raw else None
    return ScheduleItem(
        id=raw["id"],
        kind=kind,
        name=raw["name"],
        parent_id=parent_id,
        predecessors=predecessors,
        timing=timing,
        duration=raw.get("duration"),
        pinned_start=pinned_start,
        pinned_finish=pinned_finish,
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
    if task.kind != ItemKind.TASK:
        return False
    if ctx.auto_only or task.timing == "auto":
        return _schedule_auto_task(task, ctx)
    if task.is_scheduled:
        return False
    if task.timing == "start_duration":
        return _schedule_start_duration_task(task, ctx)
    if task.timing == "start_finish":
        return _schedule_start_finish_task(task, ctx)
    if task.timing == "finish_duration":
        return _schedule_finish_duration_task(task, ctx)
    return False


def _schedule_auto_task(task: ScheduleItem, ctx: SchedulingContext) -> bool:
    """Compute start/finish for an auto-scheduled task."""
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


def _schedule_start_duration_task(task: ScheduleItem, ctx: SchedulingContext) -> bool:
    """Pin start and duration; compute finish."""
    if task.pinned_start is None or task.duration is None:
        return False
    start = task.pinned_start
    finish = ctx.calendar.task_finish(start, task.duration)
    if task.start == start and task.finish == finish:
        return False
    task.start = start
    task.finish = finish
    return True


def _schedule_start_finish_task(task: ScheduleItem, ctx: SchedulingContext) -> bool:
    """Pin start and finish; derive duration for output."""
    if task.pinned_start is None or task.pinned_finish is None:
        return False
    start = task.pinned_start
    finish = task.pinned_finish
    working_days = ctx.calendar.count_working_days(start, finish)
    duration = f"{working_days}d"
    if task.start == start and task.finish == finish and task.duration == duration:
        return False
    task.start = start
    task.finish = finish
    task.duration = duration
    return True


def _schedule_finish_duration_task(task: ScheduleItem, ctx: SchedulingContext) -> bool:
    """Pin finish and duration; back-calculate start."""
    if task.pinned_finish is None or task.duration is None:
        return False
    finish = task.pinned_finish
    start = _start_for_finish(finish, task.duration, ctx.calendar)
    if task.start == start and task.finish == finish:
        return False
    task.start = start
    task.finish = finish
    return True


def _pinned_task_bound_errors(task: ScheduleItem, ctx: SchedulingContext) -> list[str]:
    """Validate one pinned task against predecessor and parent bounds."""
    errors: list[str] = []
    parent = ctx.by_id.get(task.parent_id) if task.parent_id is not None else None

    if task.timing in {"start_duration", "start_finish"}:
        if task.pinned_start is None:
            return errors
        duration = task.duration or "1d"
        earliest = _minimum_start_from_predecessors(task, ctx, duration)
        parent_floor = _parent_earliest_start(parent, ctx) if parent else None
        if parent_floor is not None:
            earliest = max(earliest, parent_floor) if earliest is not None else parent_floor
        if earliest is not None and task.pinned_start < earliest:
            errors.append(
                f"schedule: item {task.id}: {task.timing}: start {task.pinned_start} "
                f"is before earliest allowable start {earliest}"
            )

    if task.timing == "finish_duration":
        if task.pinned_finish is None or task.duration is None:
            return errors
        earliest_finish = _minimum_finish_from_predecessors(task, ctx, task.duration)
        if earliest_finish is not None and task.pinned_finish < earliest_finish:
            errors.append(
                f"schedule: item {task.id}: finish_duration: finish {task.pinned_finish} "
                f"is before earliest allowable finish {earliest_finish}"
            )

    if task.timing == "start_finish":
        if task.pinned_start is None or task.pinned_finish is None:
            return errors
        if task.pinned_start > task.pinned_finish:
            errors.append(
                f"schedule: item {task.id}: start_finish: start {task.pinned_start} "
                f"is after finish {task.pinned_finish}"
            )
            return errors
        working_days = ctx.calendar.count_working_days(task.pinned_start, task.pinned_finish)
        if working_days < 1:
            errors.append(
                f"schedule: item {task.id}: start_finish: span has no working days "
                f"between {task.pinned_start} and {task.pinned_finish}"
            )

    return errors


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


def _minimum_finish_from_predecessors(
    item: ScheduleItem,
    ctx: SchedulingContext,
    duration: str,
) -> date | None:
    """Latest minimum finish date implied by all predecessor links."""
    if not item.predecessors:
        return None

    candidates: list[date] = []
    for link in item.predecessors:
        pred = ctx.by_id.get(link.task_id)
        if pred is None:
            return None
        candidate = _constraint_finish(link, pred, duration, ctx)
        if candidate is None:
            return None
        candidates.append(candidate)

    return max(candidates)


def _constraint_finish(
    link: PredecessorLink,
    pred: ScheduleItem,
    duration: str,
    ctx: SchedulingContext,
) -> date | None:
    """Earliest allowed finish for a successor given one predecessor link."""
    anchor_start, anchor_finish = _pred_anchors(pred, ctx)
    calendar = ctx.calendar

    if link.link_type == LinkType.FF:
        if anchor_finish is None:
            return None
        return calendar.apply_lag(anchor_finish, link.lag)
    if link.link_type == LinkType.FS:
        start = _fs_constraint_start(anchor_finish, link.lag, calendar, pred_kind=pred.kind)
        if start is None:
            return None
        return calendar.task_finish(start, duration)
    if link.link_type == LinkType.SS:
        start = _ss_constraint_start(anchor_start, link.lag, calendar)
        if start is None:
            return None
        return calendar.task_finish(start, duration)
    if link.link_type == LinkType.SF:
        if anchor_start is None:
            return None
        return calendar.apply_lag(anchor_start, link.lag)
    return None


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
        return _fs_constraint_start(anchor_finish, link.lag, ctx.calendar, pred_kind=pred.kind)
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
    *,
    pred_kind: ItemKind,
) -> date | None:
    """Finish-to-start: successor starts after predecessor finishes.

    MS Project day scheduling: zero lag means the next working day after the
    predecessor finish date. Positive lag adds that many working days from the
    finish date. Milestone predecessors with zero lag (``0FS``) start the same day.
    """
    if anchor_finish is None:
        return None
    lag_days = parse_duration_to_working_days(lag) if lag else 0
    anchor = calendar.normalize_to_working_day(anchor_finish)
    if pred_kind == ItemKind.MILESTONE and lag_days == 0:
        return anchor
    gap = lag_days if lag_days > 0 else 1
    return calendar.add_working_days(anchor, gap)


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
    for milestone in _deadline_milestone_terminals(ctx):
        _collect_critical_chain(milestone, ctx, set(), critical_ids)
    return frozenset(critical_ids)


def _deadline_milestone_terminals(ctx: SchedulingContext) -> list[ScheduleItem]:
    """Deadline milestones whose feeding chain lands exactly on the date (zero slack).

    Such a milestone and its driving chain are critical for that deadline, even
    when the chain does not set overall project finish.
    """
    return [
        milestone
        for milestone in ctx.milestones
        if milestone.milestone_date is not None
        and any(
            (pred := ctx.by_id.get(link.task_id)) is not None
            and pred.finish == milestone.milestone_date
            for link in milestone.predecessors
        )
    ]


def _critical_terminal_items(
    ctx: SchedulingContext,
    project_finish: date,
) -> list[ScheduleItem]:
    """Tasks (preferably) whose finish equals project finish.

    Deadline milestones (those with predecessors) are excluded from the fallback:
    their criticality is decided by zero-slack seeding, not by having the latest
    fixed date, so a slack deadline far in the future never counts as critical.
    """
    terminals = [
        item
        for item in ctx.items
        if item.is_scheduled and item.finish == project_finish and item.kind == ItemKind.TASK
    ]
    if terminals:
        return terminals
    return [
        item
        for item in ctx.items
        if item.is_scheduled
        and item.finish == project_finish
        and not (item.kind == ItemKind.MILESTONE and item.predecessors)
    ]


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

    if item.kind == ItemKind.MILESTONE and item.milestone_date is not None:
        # A deadline milestone's feeder is driving only with zero slack: its
        # finish lands exactly on the milestone date.
        for link in item.predecessors:
            pred = by_id.get(link.task_id)
            if pred is not None and pred.finish == item.milestone_date:
                ids.append(pred.id)

    seen: set[int] = set()
    unique: list[int] = []
    for pred_id in ids:
        if pred_id not in seen:
            seen.add(pred_id)
            unique.append(pred_id)
    return unique

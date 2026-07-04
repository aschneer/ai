"""Semantic validation for schedule data beyond JSON Schema."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

from schedule.calendar_lib import WorkingCalendar
from schedule.compute_lib import validate_milestone_reachability, validate_pinned_task_bounds
from schedule.predecessors_lib import LinkType, PredecessorLink, parse_predecessor


def validate_schedule_logic(
    schedule_data: dict[str, Any],
    calendar_data: dict[str, Any] | None,
) -> list[str]:
    """Return all logic errors for schedule data. Empty list means OK."""
    errors: list[str] = []
    items = list(_iter_schedule_items(schedule_data.get("items", [])))
    by_id: dict[int, dict[str, Any]] = {}

    errors.extend(_check_duplicate_ids(items, by_id))
    errors.extend(_check_predecessor_references(items, by_id))
    errors.extend(_check_predecessor_listing(items))
    errors.extend(_check_milestone_predecessors(items))
    errors.extend(_check_project_finish_milestone(items))
    errors.extend(_check_predecessor_format(items))
    errors.extend(_check_cyclic_dependencies(items, by_id))
    errors.extend(_check_coverage_segments(schedule_data.get("coverage", [])))

    if calendar_data is None:
        if _schedule_has_milestones(items):
            errors.append("schedule: calendar file required for logic validation")
    else:
        calendar = WorkingCalendar.from_dict(calendar_data)
        errors.extend(_check_milestone_working_days(items, calendar))
        if not errors:
            errors.extend(validate_pinned_task_bounds(schedule_data, calendar_data))
        if not errors:
            errors.extend(validate_milestone_reachability(schedule_data, calendar_data))

    return errors


def _schedule_has_milestones(items: list[tuple[dict[str, Any], int | None]]) -> bool:
    """True when the schedule contains at least one milestone item."""
    return any(raw.get("kind") == "milestone" for raw, _parent_id in items)


def _iter_schedule_items(
    items: list[Any],
    parent_id: int | None = None,
) -> Iterator[tuple[dict[str, Any], int | None]]:
    """Yield each schedule item dict with its parent ID."""
    for raw in items:
        if not isinstance(raw, dict):
            continue
        yield raw, parent_id
        if raw.get("kind") == "group":
            yield from _iter_schedule_items(raw.get("children", []), raw.get("id"))


def _check_duplicate_ids(
    items: list[tuple[dict[str, Any], int | None]],
    by_id: dict[int, dict[str, Any]],
) -> list[str]:
    """One error per duplicate ID pair (first occurrence vs duplicate)."""
    errors: list[str] = []
    first_name: dict[int, str] = {}

    for raw, _parent_id in items:
        item_id = raw.get("id")
        if not isinstance(item_id, int):
            continue
        name = raw.get("name", "")
        if item_id in by_id:
            first = first_name.get(item_id, by_id[item_id].get("name", ""))
            errors.append(f"schedule: items: duplicate id {item_id}: {first!r} and {name!r}")
        else:
            first_name[item_id] = name
            by_id[item_id] = raw

    return errors


def _check_predecessor_references(
    items: list[tuple[dict[str, Any], int | None]],
    by_id: dict[int, dict[str, Any]],
) -> list[str]:
    """Every predecessor must reference an existing item ID."""
    errors: list[str] = []
    for raw, _parent_id in items:
        item_id = raw.get("id")
        for pred_string in raw.get("predecessors", []):
            link = _parse_predecessor_or_none(pred_string)
            if link is None:
                continue
            if link.task_id not in by_id:
                errors.append(
                    f"schedule: item {item_id}: predecessor {link.task_id}: unknown task id"
                )
    return errors


def _check_predecessor_format(items: list[tuple[dict[str, Any], int | None]]) -> list[str]:
    """Predecessor strings must parse."""
    errors: list[str] = []
    for raw, _parent_id in items:
        item_id = raw.get("id")
        for pred_string in raw.get("predecessors", []):
            try:
                parse_predecessor(str(pred_string))
            except ValueError:
                errors.append(
                    f"schedule: item {item_id}: invalid predecessor format: {pred_string!r}"
                )
    return errors


def _check_predecessor_listing(items: list[tuple[dict[str, Any], int | None]]) -> list[str]:
    """Enforce predecessor listing rules from data_model.md."""
    errors: list[str] = []
    for raw, parent_id in items:
        if raw.get("kind") == "milestone":
            continue
        item_id = raw.get("id")
        links = _parse_predecessors(raw.get("predecessors", []))
        if not links:
            continue

        references_zero = any(link.task_id == 0 for link in links)

        if parent_id is None:
            if references_zero and len(links) > 1:
                errors.append(
                    f"schedule: item {item_id}: must not include 0FS when other predecessors are listed"
                )
            elif references_zero and len(links) == 1:
                link = links[0]
                if link.link_type != LinkType.FS or link.lag is not None:
                    errors.append(
                        f"schedule: item {item_id}: top-level item anchored only to project "
                        f"start must list exactly [\"0FS\"]"
                    )
            continue

        if references_zero:
            errors.append(f"schedule: item {item_id}: child items must not reference id 0")

        if len(links) == 1 and links[0].task_id == parent_id:
            link = links[0]
            if link.link_type != LinkType.SS or link.lag is not None:
                errors.append(
                    f"schedule: item {item_id}: child with only parent anchor must list "
                    f"exactly [\"{parent_id}SS\"]"
                )

    return errors


def _check_milestone_predecessors(
    items: list[tuple[dict[str, Any], int | None]],
) -> list[str]:
    """A milestone predecessor annotates a deadline: finish-to-start only, no lag.

    The milestone's date stays authoritative — these links never move it — so a
    lag or a non-FS link type would have no schedulable meaning. Self-references
    and the project-start anchor (0) are also rejected.
    """
    errors: list[str] = []
    for raw, _parent_id in items:
        if raw.get("kind") != "milestone":
            continue
        item_id = raw.get("id")
        for link in _parse_predecessors(raw.get("predecessors", [])):
            if link.link_type != LinkType.FS or link.lag is not None:
                errors.append(
                    f"schedule: milestone {item_id}: predecessor must be a bare "
                    f'"{link.task_id}FS" (finish-to-start, no lag)'
                )
            if link.task_id == item_id:
                errors.append(
                    f"schedule: milestone {item_id}: predecessor cannot reference itself"
                )
            if link.task_id == 0:
                errors.append(
                    f"schedule: milestone {item_id}: predecessor cannot reference "
                    f"project start (id 0)"
                )
    return errors


def _check_project_finish_milestone(
    items: list[tuple[dict[str, Any], int | None]],
) -> list[str]:
    """At most one milestone may be ``type: project_finish``, and it needs a feeder chain.

    The designated milestone's date is the project deadline; the critical path is the
    zero-slack chain feeding it, so it must list at least one predecessor. FS-only/no-lag
    is enforced by ``_check_milestone_predecessors`` for every milestone.
    """
    errors: list[str] = []
    designated: list[int] = []
    for raw, _parent_id in items:
        if raw.get("kind") != "milestone" or raw.get("type") != "project_finish":
            continue
        item_id = raw.get("id")
        designated.append(item_id)
        if not raw.get("predecessors"):
            errors.append(
                f"schedule: milestone {item_id}: project_finish milestone requires "
                f"a predecessor chain"
            )

    if len(designated) > 1:
        ids = ", ".join(str(item_id) for item_id in designated)
        errors.append(f"schedule: at most one project_finish milestone (found ids {ids})")

    return errors


def _check_milestone_working_days(
    items: list[tuple[dict[str, Any], int | None]],
    calendar: WorkingCalendar,
) -> list[str]:
    """Milestone dates must fall on working days."""
    errors: list[str] = []
    for raw, _parent_id in items:
        if raw.get("kind") != "milestone":
            continue
        item_id = raw.get("id")
        date_value = raw.get("date")
        if not isinstance(date_value, str):
            continue
        milestone_date = date.fromisoformat(date_value)
        if not calendar.is_working_day(milestone_date):
            errors.append(
                f"schedule: milestone {item_id}: date {milestone_date} falls on a non-working day"
            )
    return errors


def _check_coverage_segments(coverage: list[Any]) -> list[str]:
    """Coverage segments must have start <= finish and not overlap within a person."""
    errors: list[str] = []
    for entry in coverage:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "")
        spans, range_errors = _parse_coverage_spans(name, entry.get("segments", []))
        errors.extend(range_errors)
        errors.extend(_coverage_overlap_errors(name, spans))
    return errors


def _parse_coverage_spans(
    name: str,
    segments: list[Any],
) -> tuple[list[tuple[date, date]], list[str]]:
    """Return valid (start, finish) spans and one error per start-after-finish segment."""
    spans: list[tuple[date, date]] = []
    errors: list[str] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        start_value = segment.get("start")
        finish_value = segment.get("finish")
        if not isinstance(start_value, str) or not isinstance(finish_value, str):
            continue
        start = date.fromisoformat(start_value)
        finish = date.fromisoformat(finish_value)
        if start > finish:
            errors.append(
                f"schedule: coverage {name!r}: segment start {start} is after finish {finish}"
            )
            continue
        spans.append((start, finish))
    return spans, errors


def _coverage_overlap_errors(name: str, spans: list[tuple[date, date]]) -> list[str]:
    """One error per pair of overlapping spans (finish is inclusive)."""
    errors: list[str] = []
    ordered = sorted(spans)
    for (prev_start, prev_finish), (next_start, next_finish) in zip(ordered, ordered[1:]):
        if next_start <= prev_finish:
            errors.append(
                f"schedule: coverage {name!r}: segments overlap "
                f"({prev_start}–{prev_finish} and {next_start}–{next_finish})"
            )
    return errors


def _check_cyclic_dependencies(
    items: list[tuple[dict[str, Any], int | None]],
    by_id: dict[int, dict[str, Any]],
) -> list[str]:
    """Predecessor graph must be acyclic among tasks, groups, and milestones."""
    graph: dict[int, list[int]] = {}
    for raw, _parent_id in items:
        kind = raw.get("kind")
        if kind not in {"task", "group", "milestone"}:
            continue
        item_id = raw.get("id")
        if not isinstance(item_id, int):
            continue
        preds: list[int] = []
        for pred_string in raw.get("predecessors", []):
            link = _parse_predecessor_or_none(pred_string)
            if link is not None and link.task_id in by_id:
                preds.append(link.task_id)
        graph[item_id] = preds

    cycle = _find_cycle(graph)
    if cycle is None:
        return []

    chain = " → ".join(str(node) for node in cycle)
    return [f"schedule: cyclic predecessor dependency: {chain}"]


def _find_cycle(graph: dict[int, list[int]]) -> list[int] | None:
    """Return one cycle as a list of node IDs, or None if acyclic."""
    visited: set[int] = set()
    stack: list[int] = []

    def dfs(node: int) -> list[int] | None:
        visited.add(node)
        stack.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in graph:
                continue
            if neighbor in stack:
                idx = stack.index(neighbor)
                return stack[idx:]
            if neighbor not in visited:
                found = dfs(neighbor)
                if found is not None:
                    return found
        stack.pop()
        return None

    for node in graph:
        if node not in visited:
            found = dfs(node)
            if found is not None:
                return found
    return None


def _parse_predecessors(values: list[Any]) -> list[PredecessorLink]:
    links: list[PredecessorLink] = []
    for value in values:
        link = _parse_predecessor_or_none(value)
        if link is not None:
            links.append(link)
    return links


def _parse_predecessor_or_none(value: Any) -> PredecessorLink | None:
    try:
        return parse_predecessor(str(value))
    except ValueError:
        return None

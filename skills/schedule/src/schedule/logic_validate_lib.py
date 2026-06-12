"""Semantic validation for schedule data beyond JSON Schema."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

from schedule.calendar_lib import WorkingCalendar
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
    errors.extend(_check_predecessor_format(items))
    errors.extend(_check_cyclic_dependencies(items, by_id))

    if calendar_data is not None:
        calendar = WorkingCalendar.from_dict(calendar_data)
        errors.extend(_check_milestone_working_days(items, calendar))

    return errors


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
        if raw.get("kind") == "milestone":
            continue
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
        if raw.get("kind") == "milestone":
            continue
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
            continue

        if references_zero:
            errors.append(f"schedule: item {item_id}: child items must not reference id 0")

        if len(links) == 1:
            link = links[0]
            if (
                link.task_id == parent_id
                and link.link_type == LinkType.SS
                and link.lag is None
            ):
                continue

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


def _check_cyclic_dependencies(
    items: list[tuple[dict[str, Any], int | None]],
    by_id: dict[int, dict[str, Any]],
) -> list[str]:
    """Predecessor graph must be acyclic among tasks and groups."""
    graph: dict[int, list[int]] = {}
    for raw, _parent_id in items:
        kind = raw.get("kind")
        if kind not in {"task", "group"}:
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

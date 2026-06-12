"""Parse MS Project-style predecessor strings and duration notation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

PREDECESSOR_PATTERN = re.compile(
    r"^(?P<task_id>\d+)(?:(?P<link_type>FS|SS|FF|SF)(?P<lag>[+-]\d+[dw])?)?$"
)
DURATION_PATTERN = re.compile(r"^(?P<sign>[+-]?)(?P<amount>\d+)(?P<unit>[dw])$")


class LinkType(str, Enum):
    """Predecessor link type — Microsoft Project semantics."""

    FS = "FS"
    SS = "SS"
    FF = "FF"
    SF = "SF"


@dataclass(frozen=True)
class PredecessorLink:
    """One parsed predecessor reference from a schedule item."""

    task_id: int
    link_type: LinkType
    lag: str | None = None


def parse_predecessor(value: str) -> PredecessorLink:
    """Parse a single predecessor string such as ``5FS`` or ``7SS+2d``."""
    match = PREDECESSOR_PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"invalid predecessor format: {value!r}")
    link_type = LinkType(match.group("link_type") or LinkType.FS.value)
    return PredecessorLink(
        task_id=int(match.group("task_id")),
        link_type=link_type,
        lag=match.group("lag"),
    )


def parse_predecessors(values: list[str]) -> list[PredecessorLink]:
    """Parse a YAML predecessors list."""
    return [parse_predecessor(value) for value in values]


def parse_duration_to_working_days(value: str) -> int:
    """Convert a duration or lag string (``4d``, ``2w``, ``+3d``) to working days."""
    match = DURATION_PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"invalid duration format: {value!r}")
    sign = -1 if match.group("sign") == "-" else 1
    amount = int(match.group("amount"))
    unit = match.group("unit")
    working_days = amount * 5 if unit == "w" else amount
    return sign * working_days

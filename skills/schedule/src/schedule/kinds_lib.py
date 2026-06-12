"""Schedule item kind discriminator."""

from __future__ import annotations

from enum import Enum


class ItemKind(str, Enum):
    """Schedule item discriminator — matches the ``kind`` field in YAML."""

    MILESTONE = "milestone"
    TASK = "task"
    GROUP = "group"

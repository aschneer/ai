"""Git churn signal: how often each file changed recently (PRD 4.1.4).

Churn is measured per file (commit count over a trailing window), which is cheap
and directional — matching triage's purpose (decision 2026-06-28 19:45). If the
target is not a git repository, churn is unavailable and reported as None so the
run continues on the remaining signals (decision 2026-06-28 17:48).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_CHURN_WINDOW_DAYS = 90


def is_git_repo(target_dir: Path) -> bool:
    """Whether ``target_dir`` is inside a git working tree."""
    result = _run_git(target_dir, ["rev-parse", "--is-inside-work-tree"])
    return result is not None and result.strip() == "true"


def file_churn(target_dir: Path, relative_paths: set[str]) -> dict[str, int]:
    """Return a commit count per file over the churn window.

    Counts commits in the last ``_CHURN_WINDOW_DAYS`` days that touched each path.
    A single ``git log`` pass over the window attributes commits to files by their
    changed-path lists. Paths with no commits are reported as 0.
    """
    counts: dict[str, int] = {path: 0 for path in relative_paths}
    log = _run_git(
        target_dir,
        ["log", f"--since={_CHURN_WINDOW_DAYS} days ago", "--name-only", "--pretty=format:"],
    )
    if log is None:
        return counts
    for line in log.splitlines():
        path = line.strip()
        if path in counts:
            counts[path] += 1
    return counts


def _run_git(target_dir: Path, args: list[str]) -> str | None:
    """Run a git command in ``target_dir``; return stdout, or None on any failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(target_dir), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    return result.stdout

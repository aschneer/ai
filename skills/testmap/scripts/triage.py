#!/usr/bin/env python3
"""Score symbols by risk and emit a priority-ordered work list.

Reads <target_dir>/.coverage_cache/index.json, scores each symbol, writes
the priority back into the index, and prints the prioritized work list.

Scoring signals:
  - cyclomatic complexity (from index)
  - has_error_paths (from index)
  - sensitivity (name/path matches risky keywords)
  - call-site count (grep across the codebase)
  - git churn (commits touching the file in the last 90 days)

Usage:
    triage.py <target_dir> [--top N]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

SENSITIVE = re.compile(r"auth|crypto|password|token|secret|payment|billing|sanitize|parse|validate|permission", re.I)


def call_site_count(root: Path, symbol_name: str) -> int:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "grep", "-c", "-w", symbol_name],
            capture_output=True, text=True,
        )
        if out.returncode != 0:
            return 0
        total = 0
        for line in out.stdout.splitlines():
            _, _, n = line.rpartition(":")
            total += int(n) if n.isdigit() else 0
        return total
    except Exception:
        return 0


def churn(root: Path, file_rel: str) -> int:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "--since=90.days", "--format=%H", "--", file_rel],
            capture_output=True, text=True, check=True,
        )
        return len([l for l in out.stdout.splitlines() if l.strip()])
    except Exception:
        return 0


def score(entry: dict, root: Path) -> tuple[int, str]:
    s = 0
    name = entry["qualified_name"].rsplit(".", 1)[-1]
    if SENSITIVE.search(entry["file"]) or SENSITIVE.search(name):
        s += 5
    s += min(entry.get("complexity", 1), 20) // 2
    if entry.get("has_error_paths"):
        s += 2
    s += min(call_site_count(root, name), 40) // 4
    s += min(churn(root, entry["file"]), 20) // 2
    if s >= 10:
        bucket = "high"
    elif s >= 5:
        bucket = "medium"
    else:
        bucket = "low"
    return s, bucket


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    ap.add_argument("--top", type=int, default=50)
    args = ap.parse_args()
    root = args.target.resolve()
    index_path = root / ".coverage_cache" / "index.json"
    if not index_path.exists():
        sys.exit("no index; run build_index.py first")
    index = json.loads(index_path.read_text())

    scored = []
    for qname, entry in index.items():
        s, bucket = score(entry, root)
        entry["priority"] = bucket
        entry["priority_score"] = s
        scored.append((s, qname, bucket))

    index_path.write_text(json.dumps(index, indent=2, sort_keys=True))
    scored.sort(reverse=True)
    counts = Counter(b for _, _, b in scored)
    print(f"priority distribution: {dict(counts)}", file=sys.stderr)
    print("symbol\tscore\tpriority")
    for s, qname, bucket in scored[: args.top]:
        print(f"{qname}\t{s}\t{bucket}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

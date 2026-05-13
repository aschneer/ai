#!/usr/bin/env python3
"""Emit the list of symbols needing (re)analysis.

A symbol is stale if:
  - it has no analysis entry yet, OR
  - its current body_hash in index.json differs from the body_hash recorded
    in its analysis entry, OR
  - any test file referenced in its `covering_tests` has changed since the
    analysis timestamp.

Usage:
    find_stale.py <target_dir> [--json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def file_hash(p: Path) -> str | None:
    if not p.exists():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = args.target.resolve()
    cache = root / ".coverage_cache"
    index_path = cache / "index.json"
    analysis_path = cache / "analysis.json"
    if not index_path.exists():
        sys.exit(f"no index at {index_path}; run build_index.py first")
    index = json.loads(index_path.read_text())
    analysis = json.loads(analysis_path.read_text()) if analysis_path.exists() else {}

    stale: list[dict] = []
    for qname, entry in index.items():
        a = analysis.get(qname)
        if a is None:
            stale.append({"symbol": qname, "reason": "no_analysis"})
            continue
        if a.get("body_hash_at_analysis") != entry["body_hash"]:
            stale.append({"symbol": qname, "reason": "body_changed"})
            continue
        for test_file in a.get("covering_test_files", []):
            th = file_hash(root / test_file)
            if th != a.get("test_file_hashes", {}).get(test_file):
                stale.append({"symbol": qname, "reason": f"test_changed:{test_file}"})
                break

    if args.json:
        print(json.dumps(stale, indent=2))
    else:
        for s in stale:
            print(f"{s['symbol']}\t{s['reason']}")
        print(f"\n{len(stale)} stale of {len(index)} symbols", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

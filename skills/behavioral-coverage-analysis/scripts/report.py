#!/usr/bin/env python3
"""Render a human-readable gap report from <target_dir>/.coverage_cache/analysis.json.

Usage:
    report.py <target_dir> [--symbol QNAME] [--only-gaps]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GLYPH = {"covered": "✓", "gap": "✗", "unspecified": "?"}


def render_symbol(qname: str, entry: dict, only_gaps: bool) -> str:
    lines = [f"\n{qname}"]
    spec = entry.get("spec", "(no spec recorded)")
    lines.append(f"  spec: {spec}")
    lines.append("  behavior matrix:")
    for cell in entry.get("behavior_matrix", []):
        status = cell.get("status", "gap")
        if only_gaps and status == "covered":
            continue
        glyph = GLYPH.get(status, "?")
        line = f"    {glyph} {cell.get('input_class','?')} → {cell.get('expected','?')}"
        if status == "covered":
            tests = cell.get("tests", [])
            line += f"   [covered: {', '.join(tests) if tests else '?'}]"
        elif status == "gap":
            note = cell.get("note", "")
            line += f"   [GAP{': ' + note if note else ''}]"
        else:
            line += "   [UNSPECIFIED — clarify intent]"
        lines.append(line)
    mr = entry.get("mutation_results")
    if mr:
        total = mr.get("survived", 0) + mr.get("killed", 0)
        lines.append(f"  mutation: {mr.get('survived',0)}/{total} mutants survived ({mr.get('tool','?')})")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    ap.add_argument("--symbol")
    ap.add_argument("--only-gaps", action="store_true")
    args = ap.parse_args()
    analysis_path = args.target.resolve() / ".coverage_cache" / "analysis.json"
    if not analysis_path.exists():
        sys.exit(f"no analysis at {analysis_path}")
    analysis = json.loads(analysis_path.read_text())

    if args.symbol:
        entry = analysis.get(args.symbol)
        if entry is None:
            sys.exit(f"no analysis for {args.symbol}")
        print(render_symbol(args.symbol, entry, args.only_gaps))
        return 0

    gap_count = 0
    covered_count = 0
    for qname, entry in sorted(analysis.items()):
        has_gap = any(c.get("status") == "gap" for c in entry.get("behavior_matrix", []))
        if args.only_gaps and not has_gap:
            continue
        print(render_symbol(qname, entry, args.only_gaps))
        for c in entry.get("behavior_matrix", []):
            if c.get("status") == "gap":
                gap_count += 1
            elif c.get("status") == "covered":
                covered_count += 1
    total = gap_count + covered_count
    pct = (covered_count / total * 100) if total else 0.0
    print(f"\n--- summary: {covered_count}/{total} cells covered ({pct:.1f}%), {gap_count} gaps", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

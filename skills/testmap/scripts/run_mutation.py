#!/usr/bin/env python3
"""Dispatch a per-language mutation testing tool against a symbol or file.

Looks up the tool for the symbol's language, runs it, parses the result,
and writes mutation_results onto the analysis entry.

Usage:
    run_mutation.py <target_dir> <symbol_or_file>

Mapping:
    python      -> mutmut
    javascript  -> stryker
    typescript  -> stryker
    java        -> pitest (via mvn)
    rust        -> cargo-mutants
    go          -> gremlins
    ruby        -> mutant
    php         -> infection
    c_sharp     -> stryker (Stryker.NET)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TOOL = {
    "python": ("mutmut", ["mutmut", "run", "--paths-to-mutate"]),
    "javascript": ("stryker", ["npx", "stryker", "run"]),
    "typescript": ("stryker", ["npx", "stryker", "run"]),
    "tsx": ("stryker", ["npx", "stryker", "run"]),
    "java": ("pitest", ["mvn", "org.pitest:pitest-maven:mutationCoverage"]),
    "rust": ("cargo-mutants", ["cargo", "mutants"]),
    "go": ("gremlins", ["gremlins", "unleash"]),
    "ruby": ("mutant", ["mutant", "run"]),
    "php": ("infection", ["vendor/bin/infection"]),
    "c_sharp": ("stryker", ["dotnet", "stryker"]),
}


def find_tool(language: str):
    info = TOOL.get(language)
    if info is None:
        return None
    name, cmd = info
    if shutil.which(cmd[0]) is None and not Path(cmd[0]).exists():
        return None
    return name, cmd


def parse_summary(stdout: str) -> dict:
    survived = killed = 0
    m = re.search(r"survived[^0-9]*(\d+)", stdout, re.I)
    if m: survived = int(m.group(1))
    m = re.search(r"killed[^0-9]*(\d+)", stdout, re.I)
    if m: killed = int(m.group(1))
    return {"survived": survived, "killed": killed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    ap.add_argument("symbol_or_file")
    args = ap.parse_args()
    root = args.target.resolve()
    cache = root / ".coverage_cache"
    index = json.loads((cache / "index.json").read_text())
    analysis_path = cache / "analysis.json"
    analysis = json.loads(analysis_path.read_text()) if analysis_path.exists() else {}

    if args.symbol_or_file in index:
        entry = index[args.symbol_or_file]
        target_file = entry["file"]
        language = entry["language"]
        symbol_key = args.symbol_or_file
    else:
        target_file = args.symbol_or_file
        ext = Path(target_file).suffix
        lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".rs": "rust", ".go": "go", ".rb": "ruby", ".php": "php", ".java": "java", ".cs": "c_sharp"}
        language = lang_map.get(ext)
        if language is None:
            sys.exit(f"unknown language for {target_file}")
        symbol_key = target_file

    tool = find_tool(language)
    if tool is None:
        sys.exit(f"no mutation tool installed for language={language}")
    name, base_cmd = tool
    cmd = base_cmd + ([target_file] if name in ("mutmut", "cargo-mutants") else [])
    print(f"running {name}: {' '.join(cmd)}", file=sys.stderr)
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    result = parse_summary(proc.stdout + "\n" + proc.stderr)
    result["tool"] = name
    result["exit_code"] = proc.returncode

    entry = analysis.setdefault(symbol_key, {})
    entry["mutation_results"] = result
    analysis_path.write_text(json.dumps(analysis, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""CLI for stage 1: discover symbols in a target directory and write index.json.

Usage:
    uv run discover <target_dir> [--test-glob PATTERN ...]

Test-file globs are supplied by the agent (which infers the repo's test
conventions); no test-naming patterns are hardcoded (decision 2026-06-28 17:51).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import Path

from testmap import index_lib
from testmap.discover_lib import extract_symbols
from testmap.languages_lib import detect_language
from testmap.paths_lib import data_file, ensure_output_dir, output_dir

_CONFIG_NAME = "testmap_config.json"


def main(argv: list[str] | None = None) -> int:
    """Entry point: walk the target directory and write/merge index.json."""
    args = _parse_args(argv)
    target_dir = Path(args.target_dir).resolve()
    if not target_dir.is_dir():
        print(f"error: target directory not found: {target_dir}", file=sys.stderr)
        return 1

    config = _load_config(target_dir)
    languages_filter = config.get("languages")
    exclude = config.get("exclude", [])

    records, parse_error_files = _discover(target_dir, exclude, languages_filter, args.test_glob)

    ensure_output_dir(target_dir)
    index_path = data_file(target_dir, "index.json")
    merged = index_lib.merge_index(
        index_lib.load_index(index_path), index_lib.build_index(records)
    )
    index_lib.save_index(index_path, merged)

    _print_summary(merged, index_path)
    if parse_error_files:
        print(
            f"warning: {parse_error_files} file(s) had parse errors; some symbols may be "
            f"missing or misparsed (common with macro-heavy C/C++).",
            file=sys.stderr,
        )
    return 0


def _discover(
    target_dir: Path,
    exclude: list[str],
    languages_filter: list[str] | None,
    test_globs: list[str],
) -> tuple[list[dict], int]:
    """Extract symbol records and count files with parse errors, across the target."""
    records: list[dict] = []
    parse_error_files = 0
    for path in _source_files(target_dir, exclude, languages_filter):
        language = detect_language(path)
        relative_path = path.relative_to(target_dir).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        is_test_file = _matches_any(relative_path, test_globs)
        symbols, had_error = extract_symbols(
            relative_path, source, language, is_test_file=is_test_file
        )
        records.extend(symbols)
        if had_error:
            parse_error_files += 1
    return records, parse_error_files


def _source_files(
    target_dir: Path, exclude: list[str], languages_filter: list[str] | None
):
    """Yield supported source files under the target, skipping output and excludes."""
    out_dir = output_dir(target_dir)
    for path in sorted(target_dir.rglob("*")):
        if not path.is_file() or out_dir in path.parents:
            continue
        language = detect_language(path)
        if language is None:
            continue
        if languages_filter is not None and language.name not in languages_filter:
            continue
        relative_path = path.relative_to(target_dir).as_posix()
        if _matches_any(relative_path, exclude):
            continue
        yield path


def _matches_any(relative_path: str, patterns: list[str]) -> bool:
    """Whether a relative path matches any glob pattern."""
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in patterns)


def _load_config(target_dir: Path) -> dict:
    """Load testmap_config.json if present, else return an empty config (PRD 1.4)."""
    config_path = target_dir / _CONFIG_NAME
    if not config_path.is_file():
        return {}
    with config_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _print_summary(index: dict[str, dict], index_path: Path) -> None:
    """Print discovery counts by kind."""
    counts = {"function": 0, "method": 0, "class": 0}
    for record in index.values():
        counts[record["kind"]] += 1
    total = len(index)
    print(
        f"discovered {total} symbols "
        f"({counts['function']} functions, {counts['method']} methods, "
        f"{counts['class']} classes) -> {index_path}"
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Discover symbols and write index.json.")
    parser.add_argument("target_dir", help="directory to analyze")
    parser.add_argument(
        "--test-glob",
        action="append",
        default=[],
        metavar="PATTERN",
        help="glob (relative to target) marking test files; repeatable",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())

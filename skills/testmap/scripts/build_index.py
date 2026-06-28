#!/usr/bin/env python3
"""Build or update the symbol index for a target directory.

Walks every source file under <target_dir> using tree-sitter, extracts every
function, method, and class, and writes <target_dir>/.coverage_cache/index.json.

Re-running updates only entries whose body hash changed.

Usage:
    build_index.py <target_dir>

Requirements:
    pip install tree-sitter tree-sitter-languages
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from tree_sitter_languages import get_language, get_parser
except ImportError:
    sys.exit("missing dependency: pip install tree-sitter tree-sitter-languages")


LANG_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "c_sharp",
    ".php": "php",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".swift": "swift",
    ".scala": "scala",
}

FUNCTION_NODE_TYPES = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "method_declaration",
    "function_item",
    "arrow_function",
    "constructor_declaration",
}
CLASS_NODE_TYPES = {
    "class_definition",
    "class_declaration",
    "struct_item",
    "impl_item",
    "trait_item",
    "interface_declaration",
}
ERROR_TOKENS = ("raise ", "throw ", "panic!", "return Err", "return error")


@dataclass
class Symbol:
    qualified_name: str
    kind: str
    file: str
    start_line: int
    end_line: int
    language: str
    signature: str
    signature_hash: str
    body_hash: str
    complexity: int
    has_error_paths: bool


def file_lang(path: Path) -> str | None:
    return LANG_BY_EXT.get(path.suffix.lower())


def iter_source_files(root: Path):
    skip = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".coverage_cache"}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in skip for part in p.parts):
            continue
        if file_lang(p):
            yield p


def hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def estimate_complexity(body: str) -> int:
    keywords = (" if ", " elif ", " else ", " for ", " while ", " case ", " catch ", " when ", "&&", "||", " and ", " or ", "?")
    return 1 + sum(body.count(k) for k in keywords)


def find_name_child(node, source: bytes) -> str:
    for child in node.children:
        if child.type in ("identifier", "property_identifier", "type_identifier", "field_identifier", "name"):
            return source[child.start_byte:child.end_byte].decode("utf8", errors="replace")
    return "<anonymous>"


def extract_symbols(path: Path, root: Path) -> list[Symbol]:
    lang = file_lang(path)
    if lang is None:
        return []
    try:
        parser = get_parser(lang)
    except Exception:
        return []
    source = path.read_bytes()
    tree = parser.parse(source)
    rel = path.relative_to(root).as_posix()
    out: list[Symbol] = []

    def walk(node, scope: list[str]):
        is_func = node.type in FUNCTION_NODE_TYPES
        is_class = node.type in CLASS_NODE_TYPES
        if is_func or is_class:
            name = find_name_child(node, source)
            qual_parts = scope + [name]
            kind = "class" if is_class else ("method" if scope else "function")
            qualified = f"{rel}::{'.'.join(qual_parts)}"
            body_bytes = source[node.start_byte:node.end_byte]
            body_text = body_bytes.decode("utf8", errors="replace")
            first_line_end = body_text.find("\n")
            signature = body_text[:first_line_end] if first_line_end != -1 else body_text
            out.append(Symbol(
                qualified_name=qualified,
                kind=kind,
                file=rel,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                language=lang,
                signature=signature.strip(),
                signature_hash=hash_bytes(signature.encode("utf8")),
                body_hash=hash_bytes(body_bytes),
                complexity=estimate_complexity(body_text),
                has_error_paths=any(tok in body_text for tok in ERROR_TOKENS),
            ))
            new_scope = qual_parts if is_class else scope
        else:
            new_scope = scope
        for child in node.children:
            walk(child, new_scope)

    walk(tree.root_node, [])
    return out


def current_commit(root: Path) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return out.stdout.strip()
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    args = ap.parse_args()
    root = args.target.resolve()
    if not root.is_dir():
        sys.exit(f"not a directory: {root}")

    cache_dir = root / ".coverage_cache"
    cache_dir.mkdir(exist_ok=True)
    index_path = cache_dir / "index.json"
    meta_path = cache_dir / "meta.json"

    existing: dict[str, dict] = {}
    if index_path.exists():
        existing = json.loads(index_path.read_text())

    new_index: dict[str, dict] = {}
    changed: list[str] = []
    for src in iter_source_files(root):
        for sym in extract_symbols(src, root):
            prev = existing.get(sym.qualified_name)
            entry = asdict(sym)
            if prev and prev.get("body_hash") == sym.body_hash:
                entry["last_analyzed"] = prev.get("last_analyzed")
                entry["last_commit"] = prev.get("last_commit")
                entry["priority"] = prev.get("priority")
            else:
                entry["last_analyzed"] = None
                entry["last_commit"] = None
                entry["priority"] = None
                changed.append(sym.qualified_name)
            new_index[sym.qualified_name] = entry

    index_path.write_text(json.dumps(new_index, indent=2, sort_keys=True))
    meta = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
    meta["last_index_commit"] = current_commit(root)
    meta["symbol_count"] = len(new_index)
    meta_path.write_text(json.dumps(meta, indent=2))

    print(f"indexed {len(new_index)} symbols ({len(changed)} changed) → {index_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

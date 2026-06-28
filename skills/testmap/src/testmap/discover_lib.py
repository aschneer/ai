"""Walk a source file with tree-sitter and extract function/method/class symbols.

Produces one record per symbol with all of PRD 2.3 except the symbol_id, which
index_lib mints from these fields. The grammar binding is Rust-backed: node
accessors are methods and traversal is via the ``.walk()`` cursor (see
``decisions.md`` and ``languages_lib``).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from testmap.languages_lib import Language

_VISIBILITY_KEYWORDS = ("public", "private", "protected")


def extract_symbols(
    relative_path: str,
    source: str,
    language: Language,
    *,
    is_test_file: bool,
) -> list[dict[str, Any]]:
    """Extract all function/method/class symbol records from one source file."""
    from testmap.languages_lib import get_parser

    source_bytes = source.encode("utf-8")
    root = get_parser(language.name).parse(source).root_node()
    symbols: list[dict[str, Any]] = []
    _walk(root, language, relative_path, source_bytes, is_test_file, [], symbols)
    return symbols


def _walk(
    node: Any,
    language: Language,
    relative_path: str,
    source_bytes: bytes,
    is_test_file: bool,
    enclosing: list[str],
    out: list[dict[str, Any]],
) -> None:
    """Depth-first walk; collect symbols and carry the enclosing class/function names."""
    cursor = node.walk()
    if not cursor.goto_first_child():
        return
    while True:
        child = cursor.node()
        is_class = child.kind() in language.class_kinds
        is_function = child.kind() in language.function_kinds
        name = _type_name(child, source_bytes) if is_class else _node_name(child, source_bytes)

        if (is_class or is_function) and name is not None:
            out.append(
                _build_symbol(
                    child, language, relative_path, source_bytes, is_test_file, enclosing
                )
            )
            _walk(
                child, language, relative_path, source_bytes, is_test_file,
                enclosing + [name], out,
            )
        else:
            _walk(
                child, language, relative_path, source_bytes, is_test_file,
                enclosing, out,
            )

        if not cursor.goto_next_sibling():
            break


def _build_symbol(
    node: Any,
    language: Language,
    relative_path: str,
    source_bytes: bytes,
    is_test_file: bool,
    enclosing: list[str],
) -> dict[str, Any]:
    """Build one symbol record (PRD 2.3 fields, minus symbol_id)."""
    is_class = node.kind() in language.class_kinds
    name = _type_name(node, source_bytes) if is_class else _node_name(node, source_bytes)
    node_bytes = source_bytes[node.start_byte() : node.end_byte()]
    signature = _signature(node_bytes)
    receiver_type = None if is_class else _receiver_type(node, source_bytes)
    name_path = enclosing + ([receiver_type, name] if receiver_type else [name])

    return {
        "qualified_name": ".".join(name_path),
        "kind": _symbol_kind(is_class, enclosing, receiver_type),
        "file_path": relative_path,
        "start_line": node.start_position().row + 1,
        "end_line": node.end_position().row + 1,
        "language": language.name,
        "signature": signature,
        "body_hash": _sha256(node_bytes),
        "signature_hash": _sha256(signature.encode("utf-8")),
        "cyclomatic_complexity": _complexity(node_bytes, language),
        "has_error_paths": _has_error_paths(node_bytes, language),
        "decorators": _decorators(node, source_bytes),
        "visibility": _visibility(signature, name, language),
        "is_test_file": is_test_file,
    }


def _symbol_kind(is_class: bool, enclosing: list[str], receiver_type: str | None) -> str:
    """Classify as class, method, or function (PRD 2.3.2).

    A function is a method if it is nested inside a type (enclosing) or carries a
    receiver (Go-style methods declared outside the type body).
    """
    if is_class:
        return "class"
    return "method" if enclosing or receiver_type else "function"


def _node_name(node: Any, source_bytes: bytes) -> str | None:
    """Return a symbol's declared name via the grammar's ``name`` field, if present."""
    return _field_text(node, "name", source_bytes)


def _type_name(node: Any, source_bytes: bytes) -> str | None:
    """Return a type's name; falls back to the ``type`` field for unnamed nodes (Rust impl)."""
    return _node_name(node, source_bytes) or _field_text(node, "type", source_bytes)


def _receiver_type(node: Any, source_bytes: bytes) -> str | None:
    """Return the receiver's type name for a Go-style method, else None (PRD 2.3.1)."""
    receiver = node.child_by_field_name("receiver")
    if receiver is None:
        return None
    text = source_bytes[receiver.start_byte() : receiver.end_byte()].decode("utf-8", "replace")
    identifiers = re.findall(r"[A-Za-z_]\w*", text)
    return identifiers[-1] if identifiers else None


def _signature(node_bytes: bytes) -> str:
    """First non-annotation line of the node (skips leading @decorator/annotation lines)."""
    for line in node_bytes.decode("utf-8", "replace").splitlines():
        if not line.lstrip().startswith("@"):
            return line
    return node_bytes.split(b"\n", 1)[0].decode("utf-8", "replace")


def _field_text(node: Any, field: str, source_bytes: bytes) -> str | None:
    """Return the source text of a named child field, or None if absent."""
    child = node.child_by_field_name(field)
    if child is None:
        return None
    return source_bytes[child.start_byte() : child.end_byte()].decode("utf-8", "replace")


def _sha256(data: bytes) -> str:
    """Return the hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def _complexity(node_bytes: bytes, language: Language) -> int:
    """Estimate cyclomatic complexity as 1 + branch-keyword occurrences (PRD 2.3.9)."""
    text = node_bytes.decode("utf-8", "replace")
    return 1 + sum(_keyword_count(text, kw) for kw in language.branch_keywords)


def _has_error_paths(node_bytes: bytes, language: Language) -> bool:
    """Whether any error-path keyword appears in the body (PRD 2.3.10)."""
    text = node_bytes.decode("utf-8", "replace")
    return any(_keyword_count(text, kw) > 0 for kw in language.error_keywords)


def _keyword_count(text: str, keyword: str) -> int:
    """Count keyword occurrences; word-boundary for word keywords, literal for symbols."""
    if keyword[0].isalpha():
        return len(re.findall(rf"\b{re.escape(keyword)}\b", text))
    return text.count(keyword)


def _decorators(node: Any, source_bytes: bytes) -> list[str]:
    """Extract decorator/annotation names (PRD 2.3.11); best-effort, empty when absent.

    Covers Python ``decorated_definition`` parents and ``modifiers``-style annotation
    children (Java/Kotlin/C#/TS). Other languages return an empty list.
    """
    names: list[str] = []
    parent = node.parent()
    if parent is not None and parent.kind() == "decorated_definition":
        names.extend(_decorator_names(parent, source_bytes, "decorator"))
    names.extend(_decorator_names(node, source_bytes, "modifiers"))
    return names


def _decorator_names(node: Any, source_bytes: bytes, container_kind: str) -> list[str]:
    """Collect ``@``-prefixed identifier names from decorator/modifier child nodes."""
    names: list[str] = []
    cursor = node.walk()
    if not cursor.goto_first_child():
        return names
    while True:
        child = cursor.node()
        if child.kind() == container_kind:
            text = source_bytes[child.start_byte() : child.end_byte()].decode("utf-8", "replace")
            names.extend(token.lstrip("@") for token in re.findall(r"@[A-Za-z_][\w.]*", text))
        if not cursor.goto_next_sibling():
            break
    return names


def _visibility(signature: str, name: str, language: Language) -> str:
    """Infer access modifier from the signature, with Python's underscore convention.

    Scans the signature line for an explicit modifier (covers languages with C-style
    modifiers); falls back to Python naming convention; defaults to public (PRD 2.3.12).
    """
    for keyword in _VISIBILITY_KEYWORDS:
        if re.search(rf"\b{keyword}\b", signature):
            return keyword
    if language.name == "python" and name.startswith("_"):
        return "private"
    return "public"

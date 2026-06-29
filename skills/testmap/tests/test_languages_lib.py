"""Tests for per-language data and lookups."""

from __future__ import annotations

from pathlib import Path

import pytest

from testmap import languages_lib


def test_detect_language_by_extension() -> None:
    assert languages_lib.detect_language(Path("a.py")).name == "python"
    assert languages_lib.detect_language(Path("a.go")).name == "go"
    assert languages_lib.detect_language(Path("a.ts")).name == "typescript"


def test_detect_language_is_case_insensitive() -> None:
    assert languages_lib.detect_language(Path("a.TSX")).name == "tsx"


def test_detect_language_unknown_extension_returns_none() -> None:
    assert languages_lib.detect_language(Path("a.unknown")) is None
    assert languages_lib.detect_language(Path("README")) is None


def test_header_routes_to_cpp_not_c() -> None:
    # .h is ambiguous; routed to C++ so the superset grammar parses C++ headers.
    assert languages_lib.detect_language(Path("a.h")).name == "cpp"
    assert languages_lib.detect_language(Path("a.c")).name == "c"


def test_get_language_known_and_unknown() -> None:
    assert languages_lib.get_language("rust").name == "rust"
    with pytest.raises(KeyError):
        languages_lib.get_language("cobol")


def test_all_languages_have_unique_names() -> None:
    names = [lang.name for lang in languages_lib.LANGUAGES]
    assert len(names) == len(set(names))


def test_cpp_languages_have_reserved_names() -> None:
    assert "namespace" in languages_lib.get_language("cpp").reserved_names
    assert "namespace" in languages_lib.get_language("c").reserved_names


def test_non_cpp_languages_have_no_reserved_names() -> None:
    assert languages_lib.get_language("python").reserved_names == ()


def test_get_parser_loads_and_caches() -> None:
    parser = languages_lib.get_parser("python")
    assert parser is not None
    # Cached: same object on repeat calls.
    assert languages_lib.get_parser("python") is parser


def test_declared_node_kinds_appear_in_a_real_parse() -> None:
    # Guards against typos in the per-language node-kind lists.
    samples = {
        "python": "class C:\n def m(self): pass\ndef f(): pass\n",
        "go": "package p\nfunc f(){}\ntype T struct{}\n",
        "java": "class C { void m(){} }\n",
    }

    def kinds(root) -> set[str]:
        out: set[str] = set()
        cursor = root.walk()

        def rec() -> None:
            out.add(cursor.node().kind())
            if cursor.goto_first_child():
                while True:
                    rec()
                    if not cursor.goto_next_sibling():
                        break
                cursor.goto_parent()

        rec()
        return out

    for name, src in samples.items():
        lang = languages_lib.get_language(name)
        present = kinds(languages_lib.get_parser(name).parse(src).root_node())
        assert present & set(lang.class_kinds), name
        assert present & set(lang.function_kinds), name

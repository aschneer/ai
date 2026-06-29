"""Tests for tree-sitter symbol extraction."""

from __future__ import annotations

from testmap import languages_lib
from testmap.discover_lib import extract_symbols


def _extract(path: str, lang: str, src: str) -> list[dict]:
    symbols, _ = extract_symbols(path, src, languages_lib.get_language(lang), is_test_file=False)
    return symbols


def _by_name(symbols: list[dict], name: str) -> dict:
    return next(s for s in symbols if s["qualified_name"] == name)


def test_python_function_method_class() -> None:
    symbols = _extract("a.py", "python", "class C:\n    def m(self): pass\ndef f(): pass\n")
    kinds = {s["qualified_name"]: s["kind"] for s in symbols}
    assert kinds == {"f": "function", "C": "class", "C.m": "method"}


def test_method_detected_by_class_ancestor() -> None:
    # A function nested in a class is a method; a free function is not.
    symbols = _extract("a.py", "python", "class C:\n    def m(self): pass\n")
    assert _by_name(symbols, "C.m")["kind"] == "method"


def test_nested_function_is_function_not_method() -> None:
    symbols = _extract("a.py", "python", "def outer():\n    def inner(): pass\n")
    assert _by_name(symbols, "outer.inner")["kind"] == "function"


def test_go_receiver_method_qualified_with_type() -> None:
    src = "package p\nfunc (a *Account) Deposit(x int) error { return nil }\n"
    symbols = _extract("a.go", "go", src)
    deposit = _by_name(symbols, "Account.Deposit")
    assert deposit["kind"] == "method"


def test_rust_impl_method_qualified_with_type() -> None:
    src = "impl Account {\n    fn method(&self) {}\n}\nfn free() {}\n"
    symbols = _extract("a.rs", "rust", src)
    assert _by_name(symbols, "Account.method")["kind"] == "method"
    assert _by_name(symbols, "free")["kind"] == "function"


def test_cpp_function_name_from_declarator_chain() -> None:
    # C/C++ names live in the declarator chain, not a name field.
    symbols = _extract("a.cpp", "cpp", "int free_func(int a) { return a; }\n")
    assert _by_name(symbols, "free_func")["kind"] == "function"


def test_cpp_macro_misparse_is_skipped() -> None:
    # An unexpanded namespace macro misparses as a function named `namespace`;
    # it must be skipped and not become an enclosing scope.
    src = "NLOHMANN_JSON_NAMESPACE_BEGIN\nnamespace detail {\nvoid real(int j) {}\n}\n"
    symbols = _extract("a.hpp", "cpp", src)
    names = {s["qualified_name"] for s in symbols}
    assert "namespace" not in names
    assert not any(n.startswith("namespace.") for n in names)
    assert "real" in names


def test_visibility_explicit_and_python_convention() -> None:
    java = _extract("C.java", "java", "class C { private void secret() {} public void open() {} }\n")
    assert _by_name(java, "C.secret")["visibility"] == "private"
    assert _by_name(java, "C.open")["visibility"] == "public"

    py = _extract("a.py", "python", "def _hidden(): pass\ndef shown(): pass\n")
    assert _by_name(py, "_hidden")["visibility"] == "private"
    assert _by_name(py, "shown")["visibility"] == "public"


def test_decorators_extracted_python_and_java() -> None:
    py = _extract("a.py", "python", "@property\ndef p(self): pass\n")
    assert "property" in _by_name(py, "p")["decorators"]

    java = _extract("C.java", "java", "class C { @Override public void m() {} }\n")
    assert "Override" in _by_name(java, "C.m")["decorators"]


def test_signature_skips_leading_annotation_lines() -> None:
    java = _extract("C.java", "java", "class C {\n    @Override\n    public void m() {}\n}\n")
    assert _by_name(java, "C.m")["signature"].strip().startswith("public void m")


def test_complexity_counts_branches() -> None:
    src = "def f(x):\n    if x:\n        return 1\n    for i in x:\n        pass\n    return 0\n"
    symbols = _extract("a.py", "python", src)
    # 1 baseline + if + for
    assert _by_name(symbols, "f")["cyclomatic_complexity"] == 3


def test_error_paths_detected_for_raise() -> None:
    src = "def f(x):\n    if x:\n        raise ValueError()\n    return x\n"
    assert _by_name(_extract("a.py", "python", src), "f")["has_error_paths"] is True


def test_no_error_paths_when_absent() -> None:
    assert _by_name(_extract("a.py", "python", "def f(): return 1\n"), "f")["has_error_paths"] is False


def test_body_hash_changes_with_body_signature_hash_stable() -> None:
    a = _by_name(_extract("a.py", "python", "def f(x):\n    return x\n"), "f")
    b = _by_name(_extract("a.py", "python", "def f(x):\n    return x + 1\n"), "f")
    assert a["body_hash"] != b["body_hash"]
    assert a["signature_hash"] == b["signature_hash"]


def test_is_test_file_flag_propagates() -> None:
    symbols, _ = extract_symbols(
        "t.py", "def f(): pass\n", languages_lib.get_language("python"), is_test_file=True
    )
    assert symbols[0]["is_test_file"] is True


def test_line_numbers_are_one_based() -> None:
    symbols = _extract("a.py", "python", "\n\ndef f(): pass\n")
    assert _by_name(symbols, "f")["start_line"] == 3


def test_parse_error_flag_reports_clean_and_broken() -> None:
    _, clean = extract_symbols("a.py", "def f(): pass\n", languages_lib.get_language("python"), is_test_file=False)
    assert clean is False
    _, broken = extract_symbols("a.hpp", "NLOHMANN_BEGIN\nnamespace d {\n}\n", languages_lib.get_language("cpp"), is_test_file=False)
    assert broken is True


def test_empty_source_yields_no_symbols() -> None:
    assert _extract("a.py", "python", "") == []

"""Per-language data: extensions, tree-sitter node kinds, keywords, mutation tools.

Pure data and lookups. The grammar binding (``tree-sitter-language-pack``) is
Rust-backed: node accessors are methods, not properties (``node().kind()``), and
traversal uses the ``.walk()`` cursor (see ``decisions.md``). Grammars load lazily
— only languages whose extensions appear in the target are ever parsed.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Language:
    """Everything discovery and triage need to know about one language."""

    name: str
    extensions: tuple[str, ...]
    function_kinds: tuple[str, ...]
    class_kinds: tuple[str, ...]
    branch_keywords: tuple[str, ...]
    error_keywords: tuple[str, ...]
    mutation_tool: str | None = None
    # Reserved words that can never be a real symbol name. If discovery extracts one
    # of these as a name it indicates a parse error — typically an unexpanded C/C++
    # preprocessor macro (e.g. NLOHMANN_JSON_NAMESPACE_BEGIN) misparsed as a function.
    # Such nodes are skipped so their misparsed children are not nested under a phantom.
    reserved_names: tuple[str, ...] = ()


# Branch keywords used for the cyclomatic-complexity estimate (PRD 2.3.9). C-family
# control-flow words cover most languages; per-language entries add the rest.
_C_BRANCH = ("if", "else", "for", "while", "case", "catch", "&&", "||", "?")

# C/C++ keywords that surface as bogus symbol names when a macro confuses the parser.
_CPP_RESERVED = (
    "namespace", "template", "class", "struct", "union", "enum", "public", "private",
    "protected", "typename", "using", "typedef", "inline", "static", "constexpr",
    "explicit", "virtual", "friend", "operator", "return", "if", "for", "while", "switch",
)

LANGUAGES: tuple[Language, ...] = (
    Language(
        name="python",
        extensions=(".py",),
        function_kinds=("function_definition",),
        class_kinds=("class_definition",),
        branch_keywords=("if", "elif", "else", "for", "while", "except", "and", "or"),
        error_keywords=("raise",),
        mutation_tool="mutmut",
    ),
    Language(
        name="javascript",
        extensions=(".js", ".jsx", ".mjs", ".cjs"),
        function_kinds=("function_declaration", "function", "arrow_function", "method_definition"),
        class_kinds=("class_declaration",),
        branch_keywords=_C_BRANCH,
        error_keywords=("throw",),
        mutation_tool="stryker",
    ),
    Language(
        name="typescript",
        extensions=(".ts",),
        function_kinds=("function_declaration", "function", "arrow_function", "method_definition"),
        class_kinds=("class_declaration", "interface_declaration"),
        branch_keywords=_C_BRANCH,
        error_keywords=("throw",),
        mutation_tool="stryker",
    ),
    Language(
        name="tsx",
        extensions=(".tsx",),
        function_kinds=("function_declaration", "function", "arrow_function", "method_definition"),
        class_kinds=("class_declaration", "interface_declaration"),
        branch_keywords=_C_BRANCH,
        error_keywords=("throw",),
        mutation_tool=None,
    ),
    Language(
        name="ruby",
        extensions=(".rb",),
        function_kinds=("method",),
        class_kinds=("class", "module"),
        branch_keywords=("if", "elsif", "else", "unless", "for", "while", "until", "when", "rescue", "&&", "||"),
        error_keywords=("raise",),
        mutation_tool="mutant",
    ),
    Language(
        name="go",
        extensions=(".go",),
        function_kinds=("function_declaration", "method_declaration"),
        class_kinds=("type_declaration",),
        branch_keywords=("if", "else", "for", "switch", "case", "select", "&&", "||"),
        error_keywords=("return err", "return error"),
        mutation_tool="gremlins",
    ),
    Language(
        name="rust",
        extensions=(".rs",),
        function_kinds=("function_item",),
        class_kinds=("struct_item", "enum_item", "trait_item", "impl_item"),
        branch_keywords=("if", "else", "for", "while", "match", "&&", "||"),
        error_keywords=("panic!", "return Err", "?"),
        mutation_tool="cargo-mutants",
    ),
    Language(
        name="java",
        extensions=(".java",),
        function_kinds=("method_declaration", "constructor_declaration"),
        class_kinds=("class_declaration", "interface_declaration", "enum_declaration"),
        branch_keywords=_C_BRANCH,
        error_keywords=("throw",),
        mutation_tool="pit",
    ),
    Language(
        name="kotlin",
        extensions=(".kt", ".kts"),
        function_kinds=("function_declaration",),
        class_kinds=("class_declaration", "object_declaration"),
        branch_keywords=("if", "else", "for", "while", "when", "catch", "&&", "||"),
        error_keywords=("throw",),
        mutation_tool=None,
    ),
    Language(
        name="csharp",
        extensions=(".cs",),
        function_kinds=("method_declaration", "constructor_declaration", "local_function_statement"),
        class_kinds=("class_declaration", "interface_declaration", "struct_declaration", "record_declaration"),
        branch_keywords=_C_BRANCH,
        error_keywords=("throw",),
        mutation_tool="stryker",
    ),
    Language(
        name="php",
        extensions=(".php",),
        function_kinds=("function_definition", "method_declaration"),
        class_kinds=("class_declaration", "interface_declaration", "trait_declaration"),
        branch_keywords=("if", "elseif", "else", "for", "foreach", "while", "switch", "case", "catch", "&&", "||"),
        error_keywords=("throw",),
        mutation_tool="infection",
    ),
    Language(
        name="c",
        extensions=(".c",),
        function_kinds=("function_definition",),
        class_kinds=("struct_specifier", "union_specifier", "enum_specifier"),
        branch_keywords=_C_BRANCH,
        error_keywords=(),  # No standard error-path syntax — best-effort only (PRD 2.3.10).
        mutation_tool=None,
        reserved_names=_CPP_RESERVED,
    ),
    Language(
        name="cpp",
        extensions=(".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx"),
        function_kinds=("function_definition",),
        class_kinds=("class_specifier", "struct_specifier"),
        branch_keywords=_C_BRANCH,
        error_keywords=("throw",),  # Best-effort only (PRD 2.3.10).
        mutation_tool=None,
        reserved_names=_CPP_RESERVED,
    ),
    Language(
        name="swift",
        extensions=(".swift",),
        function_kinds=("function_declaration",),
        class_kinds=("class_declaration", "protocol_declaration"),
        branch_keywords=("if", "else", "for", "while", "switch", "case", "guard", "catch", "&&", "||"),
        error_keywords=("throw",),
        mutation_tool=None,
    ),
    Language(
        name="scala",
        extensions=(".scala", ".sc"),
        function_kinds=("function_definition",),
        class_kinds=("class_definition", "trait_definition", "object_definition"),
        branch_keywords=("if", "else", "for", "while", "match", "case", "catch", "&&", "||"),
        error_keywords=("throw",),
        mutation_tool=None,
    ),
)

_BY_NAME: dict[str, Language] = {lang.name: lang for lang in LANGUAGES}
_BY_EXTENSION: dict[str, Language] = {
    ext: lang for lang in LANGUAGES for ext in lang.extensions
}


def detect_language(path: Path) -> Language | None:
    """Return the language for a file path by extension, or None if unsupported."""
    return _BY_EXTENSION.get(path.suffix.lower())


def get_language(name: str) -> Language:
    """Return the language by name; raise KeyError if unknown."""
    return _BY_NAME[name]


@lru_cache(maxsize=None)
def get_parser(name: str) -> Any:
    """Return a tree-sitter parser for a language, loaded lazily and cached.

    Imported inside the function so importing this module never loads grammars.
    """
    from tree_sitter_language_pack import get_parser as _get_parser

    return _get_parser(name)

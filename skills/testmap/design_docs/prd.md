# Behavioral Coverage Analysis — PRD

## Overview

A Claude Code skill that measures and improves **behavioral coverage**: whether a test suite meaningfully verifies behavior (not just executes code), and generates tests to close identified gaps.

---

## 1. Inputs

1.1. The user must provide a target directory containing the code to analyze. If not provided, the skill must explicitly ask for it before proceeding.

1.2. The output directory is always `<target_dir>/coverage_analysis/`.

1.3. The output directory structure:
- 1.3.1. Files intended to be saved, committed, and version-controlled (symbol index, analysis, report) live at the root of the output directory.
- 1.3.2. Ephemeral intermediate files (if any) live in an `ephemeral/` subfolder, which should be gitignored. If no ephemeral files are produced, this subfolder is not created.

---

## 2. Symbol Discovery

2.1. The skill must walk every source file in the target directory and extract every function, method, and class using a language-aware parser (tree-sitter).

2.2. The skill must support the following languages:
- 2.2.1. Python
- 2.2.2. JavaScript
- 2.2.3. TypeScript
- 2.2.4. TSX
- 2.2.5. Ruby
- 2.2.6. Go
- 2.2.7. Rust
- 2.2.8. Java
- 2.2.9. Kotlin
- 2.2.10. C#
- 2.2.11. PHP
- 2.2.12. C
- 2.2.13. C++
- 2.2.14. Swift
- 2.2.15. Scala

2.3. Each discovered symbol must record:
- 2.3.1. Qualified name
- 2.3.2. Kind (function / method / class)
- 2.3.3. File path (relative to target directory)
- 2.3.4. Start and end line numbers
- 2.3.5. Language
- 2.3.6. Signature (first line of the symbol node)
- 2.3.7. Body hash — SHA-256 of the full symbol node bytes (signature + body); used for change detection
- 2.3.8. Signature hash — SHA-256 of the signature line only; stored separately for reference
- 2.3.9. Cyclomatic complexity estimate (branch-keyword count)
- 2.3.10. Whether explicit error paths are present (`raise`/`throw`/`panic!`/`return Err`/`return error`)

2.4. The symbol index must be stored at `<output_dir>/index.json` and committed to version control.

2.5. Re-running symbol discovery must update only symbols whose body hash changed; unchanged entries must be preserved as-is.

---

## 3. Staleness Detection

3.1. The skill must identify symbols whose analysis is stale: no analysis entry exists, body hash has changed since last analysis, or any covering test file has changed since last analysis.

---

## 4. Risk-Based Triage

4.1. The skill must score each symbol by risk using the following signals: cyclomatic complexity, presence of error paths, name/path match against security/correctness sensitivity keywords, call-site count (via grep), and git churn over the last 90 days.

4.2. Symbols must be bucketed as `high`, `medium`, or `low` priority.

4.3. Priority scores must be written back to `index.json`.

4.4. The triage output must be a priority-ordered work list, with configurable top-N limit.

---

## 5. Behavioral Analysis

5.1. For each symbol, the agent must infer a one-sentence specification from signature, types, body, docstring, and name.

5.2. The agent must enumerate input equivalence classes by walking the edge-case taxonomy checklist explicitly (not by free association). Only categories applicable to the symbol's actual input domain must be included.

5.3. The agent must enumerate expected behaviors: return values/shapes, raised exceptions, side effects, state changes. Every `raise`/`throw`/error return in the body is a required cell.

5.4. For classes, the agent must additionally analyze:
- 5.4.1. Invariants — properties that must hold across method calls.
- 5.4.2. State transitions — one cell per method × starting state.
- 5.4.3. Construction edge cases.
- 5.4.4. Lifecycle — destructors, context managers, cleanup-on-error.
- 5.4.5. Trivial data classes (no logic) require only equality, hashing, and serialization round-trip coverage.

5.5. The agent must build a behavior matrix: a list of `(input_class, expected_behavior)` cells.

5.6. The agent must locate existing tests that exercise each symbol (by grepping imports and call sites), read each test body, and judge whether the assertion meaningfully verifies the expected behavior. Weak assertions (e.g., `assert result is not None`) must not be counted as covering a cell.

5.7. Each cell must be classified as `covered`, `gap`, or `unspecified`. `unspecified` must be used when the function's behavior on an input class is genuinely ambiguous; the agent must not invent a contract.

5.8. Analysis results must be written to `<output_dir>/analysis.json` and committed to version control. Each entry includes: spec, behavior matrix with status per cell, covering test names, body hash at time of analysis, covering test file hashes, and timestamp.

---

## 6. Mutation Testing

6.1. The skill must dispatch a per-language mutation testing tool against a symbol or file: mutmut (Python), Stryker (JS/TS/C#), PIT (Java), cargo-mutants (Rust), gremlins (Go), mutant (Ruby), infection (PHP).

6.2. Mutation results (survived count, killed count, tool name, exit code) must be written to the symbol's `analysis.json` entry.

6.3. If cells are marked `covered` but mutants survive, the discrepancy must be flagged in the report.

---

## 7. Reporting

7.1. The skill must produce a gap report from `analysis.json`, rendered as both plain text (stdout) and an HTML file saved to `<output_dir>/report.html`. The HTML report must be committed to version control.

7.2. The report must display per symbol: qualified name, inferred spec, behavior matrix with ✓/✗/? glyphs per cell, covering test names for covered cells, gap notes for gap cells, and mutation results if available.

7.3. The report must include a summary: total cells, covered count, gap count, coverage percentage.

7.4. The report must support filtering to gaps-only (symbols with at least one gap cell, showing only gap and unspecified cells).

7.5. The report must support filtering to a single symbol by qualified name.

7.6. The HTML report must be self-contained (no external dependencies) and human-navigable: symbol list, jump-to-symbol links, visual distinction between covered/gap/unspecified cells.

---

## 8. Incremental Operation

8.1. The skill must not re-analyze symbols whose body hash and covering test hashes are unchanged.

8.2. The index must always be complete — every discovered symbol listed — regardless of whether it has been analyzed.

8.3. Metadata (last commit hash, run timestamp, tool versions) must be stored in `<output_dir>/meta.json`.

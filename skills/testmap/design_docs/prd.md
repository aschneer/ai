# Testmap — PRD

## Overview

A Claude Code skill that audits test suites for assertion quality, input coverage, and behavioral completeness — producing a gap report that shows exactly what's unproven.

---

## 1. Inputs

1.1. The user must provide a target directory containing the code to analyze. If not provided, the skill must explicitly ask for it before proceeding.

1.2. The output directory is always `<target_dir>/coverage_analysis/`.

1.3. The output directory structure:
- 1.3.1. Files intended to be saved, committed, and version-controlled (symbol index, analysis, report) live at the root of the output directory.
- 1.3.2. Ephemeral intermediate files (if any) live in a `temp/` subfolder, which should be gitignored. If no ephemeral files are produced, this subfolder is not created.

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
- 2.3.11. Decorator/annotation list (e.g. `@property`, `@staticmethod`, `@Override`)
- 2.3.12. Visibility/access modifier (`public`, `private`, `protected`, or inferred default)
- 2.3.13. Whether the symbol lives in a test file

2.4. The symbol index must be stored at `<output_dir>/index.json` and committed to version control.

2.5. Re-running symbol discovery must update only symbols whose body hash changed; unchanged entries must be preserved as-is.

---

## 3. Staleness Detection

3.1. The skill must identify symbols whose analysis is stale: no analysis entry exists, body hash has changed since last analysis, or any covering test file has changed since last analysis.

---

## 4. Risk-Based Triage

4.1. The skill must score each symbol by risk using the following signals:
- 4.1.1. Cyclomatic complexity
- 4.1.2. Presence of error paths
- 4.1.3. Name/path match against security/correctness sensitivity keywords
- 4.1.4. Call-site count (via grep)
- 4.1.5. Git churn over the last 90 days
- 4.1.6. Whether the symbol has no analysis entry yet (no-analysis symbols rank higher than stale ones of equivalent score)
- 4.1.7. Public API surface — symbols with public visibility rank higher than private/internal ones of equivalent score

4.2. Symbols must be bucketed as `high`, `medium`, or `low` priority.

4.3. Priority scores must be written back to `index.json`.

4.4. The triage output must be a priority-ordered work list, with configurable top-N limit.

---

## 5. Testability Analysis

5.1. For each symbol, the skill must assess and record a test difficulty rating: `high`, `medium`, or `low`, where `high` means difficult to test.

5.2. Testability must be assessed against the following signals:
- 5.2.1. **Size and cohesion** — functions that do many unrelated things (high line count + high cyclomatic complexity + multiple distinct output types) are harder to test because each test must navigate unrelated logic to reach the behavior under test.
- 5.2.2. **Dependency injection** — functions that construct their own dependencies internally (database connections, HTTP clients, file handles, clocks) rather than accepting them as parameters are hard to test in isolation.
- 5.2.3. **Global/static state** — functions that read or write global variables, module-level singletons, or static class state are hard to test because tests cannot easily control or reset that state.
- 5.2.4. **Hidden inputs** — functions whose behavior depends on environment variables, system time, random number generators, or other implicit inputs produce non-deterministic results that are hard to assert against.
- 5.2.5. **Side effects as primary output** — functions whose only observable output is a side effect (network call, file write, database mutation) with no return value require test infrastructure (mocks, spies, fixtures) to verify.
- 5.2.6. **Mixed orchestration and logic** — functions that both delegate to other functions and contain significant logic of their own are hard to test: the orchestration can't be tested without also exercising the embedded logic, and the embedded logic can't be tested without triggering the full call chain. Pure orchestrators (no logic of their own) and pure logic functions (no delegation) are both testable; functions that mix the two are not.
- 5.2.7. **Tight coupling** — functions that directly instantiate or reference concrete external systems (specific ORM models, specific HTTP libraries) rather than abstractions cannot be tested without those systems present.
- 5.2.8. **Non-determinism** — functions with inherent randomness, timing dependencies, or concurrency that is not injectable are difficult to write repeatable assertions for.

5.3. The testability rating must not affect triage priority. It is informational only — surfaced in the report to explain why gaps exist and to flag refactoring opportunities.

5.4. The test difficulty assessment must be written to `analysis.json` per symbol, including: rating (`high`/`medium`/`low`), and a brief note identifying the primary signals that drove the rating.

---

## 6. Behavioral Analysis

6.0. For each symbol, the agent must evaluate three dimensions of test quality:
- 6.0.1. **Assertion strength** — do existing tests verify the right thing, or merely that something ran without error
- 6.0.2. **Input coverage** — do tests exercise all meaningful input equivalence classes, including edge cases and error paths
- 6.0.3. **Behavioral completeness** — for every behavior the code can exhibit, is there a test that pins it

6.1. For each symbol, the agent must infer a one-sentence specification from signature, types, body, docstring, and name.

6.2. The agent must enumerate input equivalence classes by walking the edge-case taxonomy checklist explicitly (not by free association). Only categories applicable to the symbol's actual input domain must be included.

6.3. The agent must enumerate expected behaviors:
- 6.3.1. Return values and shapes
- 6.3.2. Raised exceptions — every `raise`/`throw`/error return in the body is a required cell
- 6.3.3. Side effects
- 6.3.4. State changes

6.4. For classes, the agent must additionally analyze:
- 6.4.1. Invariants — properties that must hold across method calls.
- 6.4.2. State transitions — one cell per method × starting state.
- 6.4.3. Construction edge cases.
- 6.4.4. Lifecycle — destructors, context managers, cleanup-on-error.
- 6.4.5. Trivial data classes (no logic) require only equality, hashing, and serialization round-trip coverage.

6.5. The agent must build a behavior matrix: a list of `(input_class, expected_behavior)` cells.

6.6. The agent must locate existing tests that exercise each symbol (by grepping imports and call sites), read each test body, and judge whether the assertion meaningfully verifies the expected behavior. Weak assertions (e.g., `assert result is not None`) must not be counted as covering a cell.

6.7. Each cell must be classified as `covered`, `gap`, or `unspecified`. `unspecified` must be used when the function's behavior on an input class is genuinely ambiguous; the agent must not invent a contract.

6.8. Analysis results must be written to `<output_dir>/analysis.json` and committed to version control. Each entry must include:
- 6.8.1. Inferred spec
- 6.8.2. Behavior matrix with status per cell
- 6.8.3. Covering test names per cell
- 6.8.4. Body hash at time of analysis
- 6.8.5. Covering test file hashes
- 6.8.6. Timestamp

---

## 7. Mutation Testing

7.1. The skill must dispatch a per-language mutation testing tool against a symbol or file: mutmut (Python), Stryker (JS/TS/C#), PIT (Java), cargo-mutants (Rust), gremlins (Go), mutant (Ruby), infection (PHP).

7.2. Mutation results (survived count, killed count, tool name, exit code) must be written to the symbol's `analysis.json` entry.

7.3. If cells are marked `covered` but mutants survive, the discrepancy must be flagged in the report.

---

## 8. Reporting

8.1. The skill must produce a gap report from `analysis.json`, rendered as both plain text (stdout) and an HTML file saved to `<output_dir>/report.html`. The HTML report must be committed to version control.

8.2. The report must display per symbol: qualified name, inferred spec, test difficulty rating, behavior matrix with ✓/✗/? glyphs per cell, covering test names for covered cells, gap notes for gap cells, and mutation results if available.

8.3. The report must include a summary: total cells, covered count, gap count, coverage percentage.

8.4. The report must support filtering to gaps-only (symbols with at least one gap cell, showing only gap and unspecified cells).

8.5. The report must support filtering to a single symbol by qualified name.

8.6. The HTML report must be self-contained (no external dependencies) and human-navigable: symbol list, jump-to-symbol links, visual distinction between covered/gap/unspecified cells.

---

## 9. Incremental Operation

9.1. The skill must not re-analyze symbols whose body hash and covering test hashes are unchanged.

9.2. The index must always be complete — every discovered symbol listed — regardless of whether it has been analyzed.

9.3. Metadata (last commit hash, run timestamp, tool versions, target directory path) must be stored in `<output_dir>/meta.json`.

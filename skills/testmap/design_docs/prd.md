# Testmap — PRD

## Overview

A Claude Code skill that audits test suites for assertion quality, input coverage, and behavioral completeness — producing a gap report that shows exactly what's unproven.

---

## 1. Inputs

1.1. The user must provide a target directory containing the code to analyze. If not provided, the skill must explicitly ask for it before proceeding.

1.2. The output directory is always `<target_dir>/testmap_output/`.

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

4.3. The following must be written back to `index.json` per symbol:
- 4.3.1. Priority bucket (`high`/`medium`/`low`)
- 4.3.2. Composite risk score
- 4.3.3. Raw value for each signal defined in 4.1

4.4. After building the index and completing triage, the skill must report a pre-analysis summary to the user:
- 4.4.1. Total symbols found, broken down by kind (functions, methods, classes) and by priority bucket
- 4.4.2. Number of symbols with no prior analysis vs. stale vs. up-to-date
- 4.4.3. Estimated scope of work (large symbol counts should include an explicit warning that the analysis may take significant time and tokens)

4.5. After presenting the summary, the skill must ask the user whether to:
- 4.5.1. Analyze all symbols (default)
- 4.5.2. Analyze only `high` priority symbols now, deferring the rest to future runs
- 4.5.3. Analyze a custom subset — the skill must propose a specific recommended subset (e.g., top-N by score) and ask for confirmation

4.6. The skill must proceed only after the user confirms the scope of analysis.

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
- 6.3.2. Output type contracts — guarantees about the type or shape of the return value (e.g., always returns a list, never returns None)
- 6.3.3. Raised exceptions — every `raise`/`throw`/error return in the body is a required cell
- 6.3.4. Side effects
- 6.3.5. State changes
- 6.3.6. Negative-space contracts — behaviors that must NOT occur (e.g., must not mutate input, must not leak sensitive data in error messages, must not emit certain side effects)
- 6.3.7. Async/concurrent behavior — for async functions, expected behavior under concurrent calls, cancellation, and timeout

6.4. For classes, the agent must additionally analyze:
- 6.4.1. Invariants — properties that must hold across method calls.
- 6.4.2. State transitions — one cell per method × starting state.
- 6.4.3. Construction edge cases.
- 6.4.4. Lifecycle — destructors, context managers, cleanup-on-error.
- 6.4.5. Trivial data classes (no logic) require only equality, hashing, and serialization round-trip coverage.

6.5. The agent must build a behavior matrix: a list of `(input_class, expected_behavior)` cells.

6.6. The agent must locate existing tests that exercise each symbol (by grepping imports and call sites), read each test body, and judge whether the assertion meaningfully verifies the expected behavior:
- 6.6.1. Weak assertions (e.g., `assert result is not None`) must not be counted as covering a cell.
- 6.6.2. Tests that assert on internal implementation details (private methods, internal state) rather than observable behavior must not be counted as covering a cell and must be flagged as brittle.
- 6.6.3. Parametrized tests must be unpacked — each parameter set evaluated independently as a candidate for cell coverage.
- 6.6.4. Tests that appear to depend on execution order or shared state from prior tests must be flagged as unreliable and must not be counted as covering a cell.

6.7. Each cell must be classified as `covered`, `gap`, or `unspecified`. `unspecified` must be used when the function's behavior on an input class is genuinely ambiguous; the agent must not invent a contract.

6.8. Analysis results must be written to `<output_dir>/analysis.json` and committed to version control. Each entry must include:
- 6.8.1. Inferred spec
- 6.8.2. Behavior matrix — a list of cells, each containing:
  - 6.8.2.1. Input class description
  - 6.8.2.2. Expected behavior description
  - 6.8.2.3. Status (`covered`, `gap`, or `unspecified`)
  - 6.8.2.4. Covering tests (for `covered` cells) — list of `{test_name, brittle: bool, brittle_reason?}` objects, where `brittle` flags tests that assert on implementation details or have execution-order dependencies
  - 6.8.2.5. Gap note — why the cell is uncovered (weak assertion, no test, wrong input class, etc.) (for `gap` cells)
  - 6.8.2.6. Unspecified reason — the agent's reasoning for why the behavior is ambiguous (for `unspecified` cells)
  - 6.8.2.7. Test prescription — for `gap` cells, a one-sentence description of what a test should do: what input to pass and what to assert; sufficient to write the test without re-reading the analysis
- 6.8.3. Test difficulty rating and primary signals that drove it
- 6.8.4. Body hash at time of analysis
- 6.8.5. Covering test file hashes
- 6.8.6. Timestamp

---

## 7. Mutation Testing

7.1. The skill must dispatch a per-language mutation testing tool against a symbol or file:
- 7.1.1. Python — mutmut
- 7.1.2. JavaScript — Stryker
- 7.1.3. TypeScript — Stryker
- 7.1.4. C# — Stryker
- 7.1.5. Java — PIT
- 7.1.6. Rust — cargo-mutants
- 7.1.7. Go — gremlins
- 7.1.8. Ruby — mutant
- 7.1.9. PHP — infection

7.2. Mutation results must be written to the symbol's `analysis.json` entry, including:
- 7.2.1. Survived count
- 7.2.2. Killed count
- 7.2.3. Tool name
- 7.2.4. Exit code

7.3. If cells are marked `covered` but mutants survive, the discrepancy must be flagged in the report.

---

## 8. Reporting

8.1. The skill must produce a gap report from `analysis.json`, rendered as:
- 8.1.1. `<output_dir>/report.md` — Markdown format, committed to version control
- 8.1.2. `<output_dir>/report.html` — HTML format, self-contained, committed to version control

8.2. The report must display per symbol:
- 8.2.1. Qualified name
- 8.2.2. Inferred spec
- 8.2.3. Test difficulty rating and primary signals
- 8.2.4. Behavior matrix — each cell must visually indicate its status (covered / gap / unspecified), input class, expected behavior, and covering test names
- 8.2.5. For covered cells: covering tests, with brittle tests visually distinguished and brittle reason shown
- 8.2.6. For gap cells: gap note and test prescription
- 8.2.7. For unspecified cells: unspecified reason
- 8.2.8. Mutation results, if available — survived/killed counts, tool name, and any covered-but-mutant-survived discrepancies

8.3. The report must include a summary:
- 8.3.1. Total cells
- 8.3.2. Covered count
- 8.3.3. Gap count
- 8.3.4. Unspecified count
- 8.3.5. Coverage percentage (covered / total excluding unspecified)
- 8.3.6. Brittle test count

8.4. The report must support filtering to gaps-only (symbols with at least one gap cell, showing only gap and unspecified cells).

8.5. The report must support filtering to a single symbol by qualified name.

8.6. The HTML report must be self-contained (no external dependencies) and human-navigable:
- 8.6.1. Symbol index with jump-to-symbol links
- 8.6.2. Visual distinction between covered, gap, and unspecified cells
- 8.6.3. Visual distinction for brittle tests
- 8.6.4. Collapsible sections per symbol

8.7. The report must be structured in the following sections, in order:

- 8.7.1. **Hero summary** — visually rich section combining the overall result narrative and run metadata. Must include:
  - 8.7.1.1. **Composite score (0–100)** as the visual centerpiece, displayed alongside a grade label. Formula is always the same regardless of whether mutation testing was run:
    - Base: `coverage_pct × 70` (max 70 pts; coverage_pct = covered / non-unspecified cells)
    - Brittle penalty: `(brittle_tests / total_covering_tests) × 20` (max −20 pts)
    - Unspecified penalty: `(unspecified_cells / total_cells) × 10` (max −10 pts)
    - Floor: 0; ceiling: 100
    - Mutation results are displayed separately in the KPI strip and report but do not affect the score
  - 8.7.1.2. **Grade label** derived from composite score:
    - 90–100: Excellent
    - 75–89: Good
    - 50–74: Fair
    - 25–49: Poor
    - 0–24: Critical
  - 8.7.1.3. Raw behavioral coverage % displayed alongside the composite score for reference
  - 8.7.1.4. A 2–4 sentence plain-language narrative of the key takeaway, written by the agent based on findings
  - 8.7.1.5. All run metadata fields defined in 9.3
  - The hero section sets the tone; it should be immediately informative at a glance

- 8.7.2. **KPI strip** — a row of key metrics at a glance:
  - 8.7.2.1. Overall behavioral coverage % (covered cells / total non-unspecified cells)
  - 8.7.2.2. Total gap count
  - 8.7.2.3. Total symbols analyzed
  - 8.7.2.4. High-priority symbols with gaps
  - 8.7.2.5. Brittle test count
  - 8.7.2.6. Unspecified cell count (behaviors needing human clarification)
  - 8.7.2.7. Mutation score (killed / total mutants), if mutation testing was run

- 8.7.3. **Gaps by module (Pareto)** — vertical bar chart showing gap count per module/package, sorted descending. Highlights where the most uncovered behavior lives.

- 8.7.4. **Gaps by file (Pareto)** — vertical bar chart showing gap count per file, sorted descending.

- 8.7.5. **Findings — what to fix** — a prioritized list of the most impactful gaps to address. Each entry must include:
  - 8.7.5.1. Symbol name and priority bucket
  - 8.7.5.2. Specific gaps to close (from test prescriptions)
  - 8.7.5.3. Ordered by risk × gap count descending

- 8.7.6. **Agent insights** — one or more open-ended sections where the agent surfaces notable findings not captured elsewhere: unusual patterns, systemic issues, surprising results, alternative views of the data, or anything the agent judges worth highlighting. Multiple insight blocks may be stacked if warranted. Content and structure left to agent judgment.

- 8.7.7. **Symbol coverage matrix** — the complete, authoritative dataset. All other sections are summaries derived from this. Must include:
  - 8.7.7.1. Grouped by file/module (collapsible), with per-group coverage bar, coverage %, and `N symbols · X/Y cells` summary
  - 8.7.7.2. Column header key for symbol rows: `Symbol · Priority · Cells ✓/✗ · Coverage`
  - 8.7.7.3. Per-symbol coverage bar; each symbol expands to show its spec and behavior matrix
  - 8.7.7.4. Behavior matrix column header key: `Status · Input class · Expected behavior · Covering test(s)`
  - 8.7.7.5. Each edge case is one row marked ✓ covered / ✗ gap / ? unspecified inline, with covering test name(s) for covered rows and test prescription for gap rows
  - 8.7.7.6. Controls: search (symbol / file / spec), filter chips (All, Has gaps, Fully covered, High priority, Error paths), Expand all / Collapse all acting on visible rows
  - 8.7.7.7. One-line legend defining ✓ / ✗ / ? and the coverage-% formula
  - 8.7.7.8. Modules left unanalyzed due to scope deferral listed at bottom as collapsed "module-level only" entries with a note, so search always resolves any module

- 8.7.8. **Footer** — disclaimers about how the analysis was conducted: that behavioral coverage is agent-assessed and may contain errors, that the symbol matrix is the source of truth, and that unspecified cells require human clarification before they can be tested.

---

## 9. Incremental Operation

9.1. The skill must not re-analyze symbols whose body hash and covering test hashes are unchanged.

9.2. The index must always be complete — every discovered symbol listed — regardless of whether it has been analyzed.

9.3. Metadata must be stored in `<output_dir>/meta.json`, including:
- 9.3.1. Last commit hash of the target repository
- 9.3.2. Run timestamp
- 9.3.3. Tool versions (tree-sitter, mutation tools used)
- 9.3.4. Target directory path

9.4. Before starting a new analysis run, the skill must warn the user that existing output in `testmap_output/` will be overwritten and ask for confirmation before proceeding.

---

## 10. Output Folder README

10.1. The skill must generate `<output_dir>/README.md` as part of every run, committed to version control.

10.2. The README must include:
- 10.2.1. What the folder is and its purpose
- 10.2.2. Description of each file in the folder (`index.json`, `analysis.json`, `report.md`, `report.html`, `meta.json`)
- 10.2.3. Skill name (`testmap`), described as an agent skill
- 10.2.4. Author: Andrew Schneer — GitHub profile `https://github.com/aschneer`, skill source `https://github.com/aschneer/ai/tree/main/skills/testmap`
- 10.2.5. The repository and target directory path this analysis covers
- 10.2.6. A note that the folder lives inside the analyzed target directory and the analysis covers all files and subdirectories within it
- 10.2.7. Timestamp of when the analysis was last run
- 10.2.8. Git commit hash of the target repository at the time of the last run

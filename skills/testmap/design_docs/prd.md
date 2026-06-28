# Testmap — PRD

## Overview

A Claude Code skill that audits test suites for assertion quality, input coverage, and behavioral completeness — producing a gap report that shows exactly what's unproven.

---

## 1. Inputs

1.1. The user must provide a target directory containing the code to analyze. If not provided, the skill must explicitly ask for it before proceeding.

1.2. The output directory is always `<target_dir>/testmap_output/`.

1.3. The output directory structure:
- 1.3.1. Data files (`index.json`, `triage.json`, `analysis.json`, `mutation.json`, `meta.json`, `report_content.json`, `README.md`) live at the root of the output directory and are committed to version control.
- 1.3.2. The `report/` subfolder contains static rendering assets (`report.html`, `render.js`, `chart.js`, `marked.js`) copied from the skill source on each run. It can be deleted and regenerated without data loss and is committed to version control.
- 1.3.3. Ephemeral intermediate files live in a `temp/` subfolder, which is gitignored. `temp/scope.json` (the confirmed analysis scope) is the primary ephemeral file. If no ephemeral files are produced, this subfolder is not created.

1.4. An optional `testmap_config.json` configuration file may be placed in the target directory. If absent, all defaults apply. Supported fields:
- 1.4.1. `exclude` — array of glob patterns; matching files and directories are skipped during symbol discovery (e.g. `["vendor/**", "generated/**"]`)
- 1.4.2. `languages` — array of language names; restricts analysis to this subset of supported languages (e.g. `["python", "typescript"]`)

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
- 2.3.10. Whether explicit error paths are present (`raise`/`throw`/`panic!`/`return Err`/`return error`); for C and C++ this is best-effort only (no standard error-path syntax exists)
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
- 4.1.3. Name/path match against security/correctness sensitivity keywords defined in `skills/testmap/sensitivity_keywords.md`
- 4.1.4. Git churn over the last 90 days
- 4.1.5. Whether the symbol has no analysis entry yet (no-analysis symbols rank higher than stale ones of equivalent score)
- 4.1.6. Public API surface — symbols with public visibility rank higher than private/internal ones of equivalent score

4.2. Symbols must be bucketed as `high`, `medium`, or `low` priority.

4.3. Triage results must be written to `<output_dir>/triage.json`, one entry per symbol, keyed by symbol ID. Each entry must include:
- 4.3.1. Priority bucket (`high`/`medium`/`low`)
- 4.3.2. Composite risk score
- 4.3.3. Raw value for each signal defined in 4.1

4.4. After building the index and completing triage, the skill must report a pre-analysis summary to the user:
- 4.4.1. Total symbols found, broken down by kind (functions, methods, classes) and by priority bucket
- 4.4.2. Number of symbols with no prior analysis vs. stale vs. up-to-date
- 4.4.3. Estimated scope of work (large symbol counts should include an explicit warning that the analysis may take significant time and tokens)
- 4.4.4. A notice that results will be written to `testmap_output/` and will overwrite any existing output — the user should commit any changes they want to keep before proceeding

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

7.2. Mutation results must be written to `<output_dir>/mutation.json`, one entry per symbol, keyed by symbol ID. Each entry must include:
- 7.2.1. Survived count
- 7.2.2. Killed count
- 7.2.3. Tool name
- 7.2.4. Exit code

7.3. If cells are marked `covered` but mutants survive, the discrepancy must be flagged in the report.

---

## 8. Reporting

8.1. The skill must produce a gap report as a browser-based HTML application. Files:
- 8.1.1. `<output_dir>/report/report.html` — static HTML skeleton; shipped with the skill and copied into `report/` on each run; never regenerated at runtime
- 8.1.2. `<output_dir>/report/render.js` — static JS rendering logic; shipped with the skill and copied into `report/` on each run; fetches all data files via `fetch()` at page load and populates all report sections; never regenerated at runtime
- 8.1.3. `<output_dir>/report/chart.js` — Chart.js library bundled locally; no external network dependencies permitted
- 8.1.4. `<output_dir>/report/marked.js` — Markdown parser bundled locally; used by `render.js` to render narrative summary and agent insights from markdown strings
- 8.1.5. `<output_dir>/report_content.json` — agent-generated each run; lives at the root of `testmap_output/`; contains all dynamic agent-written content. Structure: `{"narrative_summary": "<markdown>", "insights": [{"title": "<string>", "body": "<markdown>"}, ...]}`
- 8.1.6. The `report/` folder contains only static rendering assets and can be deleted and regenerated at any time without data loss. All data lives at the root of `testmap_output/`.
- 8.1.7. The report requires a local web server to view (browsers block `fetch()` on `file://`). After generating the report, the agent must print the command to start one (e.g. `python3 -m http.server 8080`).
- 8.1.8. `render.js` fetches `../index.json`, `../triage.json`, `../analysis.json`, `../report_content.json`, and (if present) `../mutation.json` at page load. Data files are never embedded in the HTML.

8.2. The report must be structured in the following sections, in order:

- 8.2.1. **Hero summary** — the visual centerpiece of the report. Must include:
  - 8.2.1.1. **Composite score (0–100)** with grade label. Formula (identical regardless of whether mutation testing was run):
    - Base: `coverage_pct × 70` (max 70 pts; `coverage_pct = covered_cells / (total_cells − unspecified_cells)`)
    - Brittle penalty: `(brittle_test_count / total_covering_tests) × 20` (max −20 pts; 0 if `total_covering_tests = 0`)
    - Unspecified penalty: `(unspecified_cells / total_cells) × 10` (max −10 pts)
    - Floor: 0; ceiling: 100
  - 8.2.1.2. **Grade label** derived from composite score:
    - 90–100: Excellent
    - 75–89: Good
    - 50–74: Fair
    - 25–49: Poor
    - 0–24: Critical
  - 8.2.1.3. Raw behavioral coverage % alongside the composite score
  - 8.2.1.4. All run metadata fields defined in 9.3
  - 8.2.1.5. A plain-language narrative summary of the key findings, written by the agent in markdown and stored in `report_content.json`; rendered here at page load
  - 8.2.1.6. Mutation results are displayed separately in the KPI strip and do not affect the composite score

- 8.2.2. **KPI strip** — key metrics at a glance:
  - 8.2.2.1. Behavioral coverage % (covered / non-unspecified cells)
  - 8.2.2.2. Total gap count
  - 8.2.2.3. Total symbols analyzed
  - 8.2.2.4. High-priority symbols with gaps
  - 8.2.2.5. Brittle test count
  - 8.2.2.6. Unspecified cell count
  - 8.2.2.7. Mutation score (killed / total mutants), if mutation testing was run

- 8.2.3. **Coverage heatmap** — a grid of files colored by coverage %; instantly shows which files are healthy vs. critically uncovered without reading tables.

- 8.2.4. **Risk vs. coverage scatter plot** — each symbol plotted as a dot: X axis = risk score, Y axis = coverage %. Top-right quadrant (high risk, low coverage) = highest-priority symbols. Makes the triage case visually immediate.

- 8.2.5. **Files needing attention** — a table of files sorted by gap count descending. Each row includes:
  - 8.2.5.1. File path
  - 8.2.5.2. Gap count
  - 8.2.5.3. Coverage %
  - 8.2.5.4. Highest-risk symbol in the file

- 8.2.6. **Brittle test distribution** — file/module breakdown of brittle test count, showing where false-confidence tests are concentrated.

- 8.2.7. **Test difficulty distribution** — breakdown of symbols by test difficulty rating (`high`/`medium`/`low`), showing what proportion of the codebase is structurally hard to test.

- 8.2.8. **Findings — what to fix** — prioritized list of most impactful gaps, ordered by risk × gap count descending. Each entry includes:
  - 8.2.8.1. Symbol name and priority bucket
  - 8.2.8.2. Specific gaps to close, drawn from test prescriptions in `analysis.json`

- 8.2.9. **Unspecified behaviors — needs human decision** — a flat table of all `unspecified` cells requiring human clarification before they can be tested. Each row includes:
  - 8.2.9.1. Symbol qualified name
  - 8.2.9.2. Input class
  - 8.2.9.3. Unspecified reason

- 8.2.10. **Agent insights** — one or more open-ended sections where the agent surfaces notable findings not captured elsewhere: unusual patterns, systemic issues, surprising results, alternative views of the data, or anything the agent judges worth highlighting. Content written by agent in markdown and stored as the `insights` array in `report_content.json`; rendered as stacked blocks at page load. Number of blocks and content left to agent judgment.

- 8.2.11. **Test prescription table** — a flat, scannable table of all gap cells across all analyzed symbols, intended as a work list for writing missing tests. Each row includes:
  - 8.2.11.1. Symbol qualified name
  - 8.2.11.2. Priority bucket
  - 8.2.11.3. Input class
  - 8.2.11.4. Expected behavior
  - 8.2.11.5. Test prescription

- 8.2.12. **Symbol coverage matrix** — the complete, authoritative dataset; all other sections are summaries derived from this. Organized in three nested levels:

  - 8.2.12.1. **Module/file level** (outermost grouping):
    - 8.2.12.1.1. Grouped by file/module, collapsible
    - 8.2.12.1.2. Per-group coverage bar and coverage %
    - 8.2.12.1.3. Per-group summary: `N symbols · X covered / Y gap / Z unspecified cells`

  - 8.2.12.2. **Symbol level** (within each module):
    - 8.2.12.2.1. Symbol name
    - 8.2.12.2.2. Priority bucket
    - 8.2.12.2.3. Covered / gap / unspecified cell counts
    - 8.2.12.2.4. Coverage % and bar
    - 8.2.12.2.5. Inferred spec (shown on expand)
    - 8.2.12.2.6. Test difficulty rating and primary signals
    - 8.2.12.2.7. Mutation results (survived/killed, tool, covered-but-survived discrepancies), if available

  - 8.2.12.3. **Behavior cell level** (within each symbol, one row per cell):
    - 8.2.12.3.1. Status indicator (covered / gap / unspecified)
    - 8.2.12.3.2. Input class
    - 8.2.12.3.3. Expected behavior
    - 8.2.12.3.4. For covered cells: covering test name(s); brittle tests visually distinguished with brittle reason
    - 8.2.12.3.5. For gap cells: gap note and test prescription
    - 8.2.12.3.6. For unspecified cells: unspecified reason

  - 8.2.12.4. **Controls**: search (symbol / file / spec), filter chips (All, Has gaps, Fully covered, High priority, Error paths), Expand all / Collapse all acting on visible rows

  - 8.2.12.5. **Legend**: one-line definition of covered / gap / unspecified and the coverage-% formula

  - 8.2.12.6. **Deferred symbol stubs**: symbols not analyzed in this run listed at bottom with a "not yet analyzed" note, so every symbol in the index is findable in the matrix

- 8.2.13. **Footer** — disclaimers: behavioral coverage is agent-assessed and may contain errors; the symbol matrix is the source of truth; unspecified cells require human clarification before they can be tested.

8.3. The report must be fully regenerable from the pipeline output files (`index.json`, `triage.json`, `analysis.json`, `mutation.json`, `meta.json`, `report_content.json`) without re-running the analysis.

---

## 9. Incremental Operation

9.1. The skill must not re-analyze symbols whose body hash and covering test hashes are unchanged.

9.2. The index must always be complete — every discovered symbol listed — regardless of whether it has been analyzed.

9.3. Metadata must be stored in `<output_dir>/meta.json`, including:
- 9.3.1. Target directory path
- 9.3.2. Target repository remote URL (if available)
- 9.3.3. Git commit hash of the target repository at time of run
- 9.3.4. Run timestamp (ISO 8601)
- 9.3.5. Scope of analysis (all symbols, high-priority only, or custom subset)
- 9.3.6. Total symbols discovered
- 9.3.7. Total symbols analyzed this run
- 9.3.8. Tool versions (tree-sitter, any mutation tools invoked)

---

## 10. Output Folder README

10.1. A `README.md` must be present in every `testmap_output/` folder. It is a static file authored as part of the skill and copied verbatim into the output folder on each run — it contains no run-specific data.

10.2. The README must be stored in the skill source at `skills/testmap/README_template.md` and copied to `<output_dir>/README.md` on every run.

10.3. The README must include:
- 10.3.1. What the `testmap_output/` folder is and its purpose
- 10.3.2. Description of each file in the folder and how to use it: `index.json`, `triage.json`, `analysis.json`, `mutation.json` (if present), `meta.json`, `report_content.json`, and the `report/` folder
- 10.3.3. A note that `report/report.html` is the primary human-readable report (requires a local web server — e.g. `python3 -m http.server 8080` from `testmap_output/`) and `meta.json` contains run-specific details about when and how the analysis was performed
- 10.3.4. A note that this folder lives inside the analyzed target directory and the analysis covers all source files and subdirectories within it
- 10.3.5. Skill name (`testmap`), described as an agent skill
- 10.3.6. Author: Andrew Schneer — GitHub profile `https://github.com/aschneer`, skill source `https://github.com/aschneer/ai/tree/main/skills/testmap`

---

## 11. Analysis CLI

The skill must provide a Python CLI (`src/testmap/analysis_cli.py`) that the agent uses to interact with `analysis.json` without loading the full file into context. All commands operate on the `analysis.json` in the output directory passed as the first argument.

11.1. Required commands:

- 11.1.1. `read <output_dir> <symbol_key>` — print one symbol's analysis entry as JSON to stdout
- 11.1.2. `write <output_dir> <symbol_key> <json>` — update one symbol's entry in `analysis.json`; creates the file if absent
- 11.1.3. `list-keys <output_dir>` — print all symbol keys, one per line
- 11.1.4. `list-stale <output_dir>` — print keys of all symbols whose analysis is stale or missing
- 11.1.5. `summary <output_dir>` — print a JSON summary of counts (total, analyzed, stale, by priority bucket) without loading full entries

11.2. Symbol keys must be stable, unique identifiers composed of `<relative_file_path>::<qualified_name>`.

11.3. All commands must exit with code 0 on success and non-zero on error, with a human-readable error message to stderr.

---

## Deferred — Implement Later

The following requirements are intentionally out of scope for the initial implementation. They are captured here for future consideration.

D.1. **Markdown report** — `<output_dir>/report.md`; a Markdown mirror of `report.html` containing the same sections and core information formatted in idiomatic Markdown; does not attempt to replicate interactive or visual-only elements (charts, collapsible UI) but conveys equivalent information in text/table form; committed to version control.

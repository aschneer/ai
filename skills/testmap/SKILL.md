---
name: testmap
description: Only use when explicitly invoked as /testmap. Audits a test suite for behavioral coverage — whether tests meaningfully verify behavior rather than merely executing code — and produces an HTML gap report. Covers assertion quality, input-class coverage, and behavioral completeness across functions, methods, and classes.
disable-model-invocation: true
---

# Testmap

## Overview

Execution-coverage tools (coverage.py, nyc, …) measure whether tests *ran* code. They say nothing about whether tests *verify* behavior — you can hit 100% line coverage with `assert True`. Testmap measures **behavioral coverage**: for each function, method, and class, did the suite exercise the meaningful input equivalence classes and pin every behavior the code can exhibit — including edge cases and error paths — with assertions that actually check the result?

The pipeline is deterministic Python for everything mechanical (discovery, hashing, triage scoring, the composite score, rendering) and **the agent for every judgment** (spec inference, enumerating input classes and behaviors, mapping tests to behaviors, judging assertion quality, classifying coverage). The agent's per-symbol output is the heart of the skill.

This is a UV project. **Run every command from the skill's own directory** (the folder containing this `SKILL.md`) using `uv run <command>`. `cd` into the skill directory first; the commands below assume that working directory. Every command supports `--help` (e.g. `uv run staleness --help`) — use it to see a command's subcommands and arguments.

## When to use

- Auditing a test suite for quality, not just line/branch percentage
- Before a release where correctness matters (auth, money, parsing untrusted input)
- When execution coverage is high but bugs keep escaping
- Auditing a specific risky function or class
- Building an incremental, persistent behavioral-coverage index for a codebase

## When NOT to use

- Execution coverage is genuinely what you want — use coverage.py / nyc instead
- Throwaway or exploratory code
- Generated code with no human-written tests expected

## Inputs

- A **target directory** — the codebase to analyze. All output lives in `<target_dir>/testmap_output/`.
- Optional `<target_dir>/testmap_config.json` — `exclude` (glob patterns to skip) and `languages` (restrict to a subset).

## Output

Everything lives under `<target_dir>/testmap_output/` (committed to the target's version control; an auto-written `.gitignore` excludes the ephemeral `temp/`):

```
index.json            every discovered symbol (complete, always)
triage.json           per-symbol risk score + priority bucket
analysis.json         per-symbol behavior matrices (agent-written)
metrics.json          composite score, grade, KPI aggregates
meta.json             run metadata (commit, timestamp, tool versions)
report_content.json   agent narrative + insights (agent-written)
report/               static HTML report (open report.html via a local server)
temp/scope.json       the confirmed analysis scope (ephemeral)
```

## Process

Work through the pipeline in order. Stages 1–3 and 6 are commands; stage 4 is your own per-symbol analysis; stage 5 (mutation) is deferred and not implemented.

### 1. Discover symbols

First infer the repo's **test-file conventions** by inspecting its layout (e.g. `tests/`, `*_test.go`, `*.spec.ts`, `test_*.py`). Then run discovery, passing those conventions as globs so test files are flagged:

```
uv run discover <target_dir> --test-glob 'tests/**' --test-glob '**/*_test.py'
```

Discovery walks every supported source file with tree-sitter and writes `index.json`. Re-runs update only symbols whose body hash changed; the index is always the complete symbol set.

### 2. Triage

```
uv run triage <target_dir>
```

Scores each symbol by risk (complexity, error paths, security/correctness sensitivity, git churn, public-API surface, whether it has no prior analysis) and writes `triage.json` with a priority bucket per symbol. Triage is directional — it orders the work, it does not decide correctness.

### 3. Staleness summary and scope confirmation

```
uv run staleness summary <target_dir>
```

This prints the pre-analysis summary — symbol counts by kind and priority, how many are unanalyzed / stale / up-to-date, and a notice that output will be overwritten. **Present this summary to the user and confirm what to analyze before proceeding.** Offer:

1. All symbols (default)
2. Only `high`-priority symbols now, deferring the rest
3. A custom subset — propose a specific recommended set (e.g. the top-N by risk) and confirm

Warn explicitly that the user should commit anything they want to keep, since output will be overwritten. Once confirmed, record the scope:

```
uv run staleness write-scope <target_dir> all
uv run staleness write-scope <target_dir> high_only
uv run staleness write-scope <target_dir> custom <symbol_id> <symbol_id> …
```

Get the work list — the symbols in scope that are stale or unanalyzed:

```
uv run query <target_dir>/testmap_output stale
```

### 4. Analyze each in-scope symbol (the core agent work)

For every symbol on the work list, read its source and its covering tests, then build its behavior matrix. Do this one symbol at a time and write each entry as you finish it (a crash then loses at most one symbol's work).

**4a. Infer the specification.** From signature, types, body, docstring, and name, write one sentence: "this symbol is supposed to ___." If genuinely ambiguous, say so — do not invent a contract.

**4b. Enumerate input equivalence classes.** Walk the **edge-case taxonomy** (`edge_case_taxonomy.md`) explicitly, category by category. Do not free-associate. For each category ask: does an instance apply to this symbol's inputs? Include only the ones that apply.

**4c. Enumerate expected behaviors.** Return values and output-type contracts, every `raise`/`throw`/error return (each distinct one is a cell), side effects, state changes, negative-space contracts (what must *not* happen — e.g. must not mutate input, must not leak secrets in errors), and for async code: cancellation, timeout, concurrent invocation.

**4d. For classes, add dimensions.** Analyze each method with object state as an extra input dimension; also cover invariants across method calls, state transitions (one cell per method × starting state), construction edge cases, and lifecycle (context managers, cleanup-on-error). Trivial data classes need only equality, hashing, and a serialization round-trip.

**4e. Build the behavior matrix** — the list of `(input_class, expected_behavior)` cells.

**4f. Map existing tests onto cells.** Find tests that exercise the symbol (grep imports and call sites) and read each body. A test covers a cell only if it passes an input in that class **and** asserts on the expected behavior meaningfully. Do not count: weak assertions (`assert result is not None`, bare truthiness), tests asserting on implementation details / private state (flag these as brittle), or tests that depend on execution order or shared state (flag as brittle). Unpack parametrized tests and judge each parameter set independently.

**4g. Classify each cell.**
- `covered` — a test exercises the input class with a meaningful assertion
- `gap` — no test, or only weak/wrong/brittle assertions
- `unspecified` — behavior on this input is genuinely ambiguous from code and docs; surface for a human decision rather than guessing

**4h. Rate test difficulty** (`high`/`medium`/`low`, informational only — does not affect priority) from structural signals: size/cohesion, self-constructed dependencies, global/static state, hidden inputs, side-effect-only output, mixed orchestration-and-logic, tight coupling, non-determinism. Note the primary signals.

**4i. Write the entry.** Emit one JSON object and write it with the analysis CLI (this keeps the multi-MB file out of your context):

```
uv run analysis-cli write <target_dir>/testmap_output/analysis.json <symbol_id> -
```

Pass the JSON on stdin (the trailing `-`). The object must conform to `schemas/analysis.schema.yaml`:

```json
{
  "spec": "one-sentence specification",
  "behavior_matrix": [
    {"input_class": "...", "expected_behavior": "...", "status": "covered",
     "covering_tests": [{"test_name": "...", "brittle": false}]},
    {"input_class": "...", "expected_behavior": "...", "status": "gap",
     "gap_note": "why uncovered", "test_prescription": "what input to pass and what to assert"},
    {"input_class": "...", "expected_behavior": "...", "status": "unspecified",
     "unspecified_reason": "why ambiguous"}
  ],
  "test_difficulty": {"rating": "medium", "signals_note": "constructs its own DB connection"},
  "body_hash": "<the symbol's body_hash from index.json>",
  "covering_test_hashes": {"tests/test_x.py": "<sha256 of that test file>"},
  "timestamp": "2026-06-29T00:00:00Z"
}
```

`body_hash` must equal the symbol's `body_hash` in `index.json` (read it with `query <output_dir> index <symbol_id>`). `covering_test_hashes` maps each covering test file to its current SHA-256, so staleness detection knows when a test changed. The timestamp is UTC and must end in `Z`. The CLI validates the entry and reports every problem at once if it fails — fix them all and rewrite.

Use `analysis-cli read` / `list-keys`, and `query … summary` to track progress without reloading the whole file.

### 5. Mutation testing — deferred

Not implemented (see `design_docs/decisions.md`). Skip it.

### 6. Report

Compute the score and metadata and copy the report assets:

```
uv run report <target_dir>
```

This writes `metrics.json` and `meta.json` and refreshes `report/`. Then write `report_content.json` yourself — the narrative summary and insights, in markdown, conforming to `schemas/report_content.schema.yaml`:

```json
{
  "narrative_summary": "Plain-language summary of the key findings, in markdown.",
  "insights": [
    {"title": "Short heading", "body": "An open-ended observation, in markdown."}
  ]
}
```

The narrative is the report's headline prose — a short plain-language summary of where the suite stands.

Insights are open-ended blocks for things the report's fixed sections do **not** already show. Those sections are: hero score, KPI strip, coverage heatmap, risk-vs-coverage scatter, files needing attention, brittle test distribution, test difficulty distribution, findings (gaps ranked by risk), unspecified behaviors, test prescriptions, and the full symbol coverage matrix. Do not write an insight that merely restates one of these (e.g. "file X has the most gaps" — the table already says so).

Use insights for cross-cutting observations that emerge from reading the code: a systemic pattern ("every error path in the auth module is untested"), a root cause ("gaps cluster where functions construct their own dependencies — hard to test by design"), a surprising finding ("the highest-risk symbol is fully covered, but with three brittle tests"), or a recommendation that spans symbols ("introduce a clock abstraction to make the time-dependent functions testable"). Each block is a `{title, body}` pair, body in markdown.

It is perfectly fine to write **no** insight blocks (`"insights": []`) when the fixed sections already tell the whole story — empty is better than padding. The number of blocks is your judgment.

The report stage installs a self-contained `serve.sh` in the output folder. To view the report (it needs a web server — browsers block `fetch()` on `file://`), the user just runs that script; it starts the server, rooted correctly, and prints a local and a remote URL to open.

Tell the user to run it, with the absolute path the report command printed:

```
<target_dir>/testmap_output/serve.sh
```

Do not start the server yourself — a server you launch dies when your session ends. The user runs `serve.sh` in their own terminal, clicks the URL matching where they are (the remote URL works from another machine, e.g. over SSH), and stops it with Ctrl-C.

## Test generation is out of scope

Testmap produces a gap report. Writing the actual missing tests is a follow-up task seeded with the report's prescriptions — not part of this skill.

## Common mistakes

| Mistake | Reality |
|---|---|
| Trusting test names | `test_empty_string` may not pass `""`. Read the body. |
| Accepting weak assertions | `assert result is not None` covers nothing. Require assertions that pin behavior. |
| Counting brittle tests as coverage | Tests on private state or with order dependencies are brittle — flag them, don't count them. |
| Free-associating edge cases | Walk the taxonomy explicitly; LLMs miss categories inconsistently otherwise. |
| Treating all inputs as one class | `list[int]` has many classes: empty, single, sorted, reverse-sorted, duplicates, negatives. Each is a cell. |
| Forgetting error paths | Every `raise`/`throw`/error return is a cell. No test triggering it is a gap. |
| Skipping a class's state machine | A method call is a cell *per starting state*. |
| Inventing an "unspecified" contract | If the spec is genuinely ambiguous, mark `unspecified` and surface it. Don't guess. |
| Re-analyzing unchanged code | Trust body-hash staleness; only analyze the work list. |
| Loading analysis.json wholesale | Use `analysis-cli` and `query`; never read the full file into context. |

## Tips

- First run on a large codebase: confirm `high_only` scope and build the index out over later runs. Leaving most of a >1000-symbol index unanalyzed for a while is correct.
- Re-run discovery + triage after a big refactor — complexity and churn shift.
- The symbol coverage matrix in the report is the authoritative dataset; every other section summarizes it.

## File reference

- `edge_case_taxonomy.md` — the input-class checklist for step 4b
- `sensitivity_keywords.md` — security/correctness keywords used by triage
- `schemas/*.schema.yaml` — the JSON contracts for every data file
- `design_docs/` — PRD, architecture, and decisions

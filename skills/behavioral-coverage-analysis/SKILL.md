---
name: behavioral-coverage-analysis
description: Use when assessing test quality across a codebase, when traditional line/branch coverage looks high but bugs still slip through, when reviewing whether tests meaningfully verify behavior rather than merely executing code, or when auditing a function/class for missing edge-case tests.
---

# Behavioral Coverage Analysis

## Overview

Traditional coverage tools measure whether tests *executed* code. They say nothing about whether tests *meaningfully verify* behavior — you can hit 100% line coverage with `assert True`. This skill measures **behavioral coverage**: for each function and class, did the test suite exercise the meaningful equivalence classes of input → output behavior, including edge cases and error paths?

The core move, per symbol: infer the spec, enumerate input equivalence classes (using the edge-case taxonomy), enumerate expected behaviors (returns, raises, side effects), build a behavior matrix, map existing tests onto cells while verifying assertion quality, classify each cell as covered / gap / unspecified, and write the result to a cache.

## When to use

- Reviewing a test suite for quality, not just quantity
- Before shipping a release where correctness matters (security, money, parsing untrusted input)
- When traditional coverage is high but bugs keep escaping
- Auditing a specific function/class flagged as risky
- Building an incremental, persistent test-coverage index for a codebase

## When NOT to use

- Project-specific test conventions that already have a custom checklist (use that)
- Pure exploratory/throwaway code
- Generated code with no human-written tests expected
- Tasks satisfied by `coverage.py`/`nyc`/etc. — if execution coverage is genuinely what you want, this skill is overkill

## Inputs

- A **target directory** (the codebase to analyze; cache and analysis live in `<target_dir>/.coverage_cache/`)
- Optional: a **symbol filter** (single function/class/file) to analyze just one entry

## Cache layout

All state lives in `<target_dir>/.coverage_cache/`:

```
index.json       every function/class/method discovered (full)
analysis.json    behavior matrices, gaps, test mappings (per-symbol)
meta.json        last commit hash, last run timestamp, tool versions
```

The **index is always complete** — every discovered symbol is listed. Triage only orders the analysis work; lower-priority entries are filled in over subsequent runs.

## Process

### 1. Build/update the index

Run `scripts/build_index.py <target_dir>`. It uses tree-sitter to walk every source file in the directory tree, extracting every function, method, and class. Each entry records signature, body hash, location, language, complexity, and whether it has explicit error paths.

If `index.json` already exists, this updates only entries whose body hash changed.

### 2. Find stale entries

Run `scripts/find_stale.py <target_dir>`. It compares cached body hashes against current source (and uses git history if available — `git log --name-only $LAST_COMMIT..HEAD`). Output: a list of symbols whose analysis is stale or missing.

### 3. Triage

Run `scripts/triage.py <target_dir>`. It scores each stale symbol by risk and emits a priority-ordered work list. Risk signals:

- Cyclomatic complexity (branch count)
- Public API surface (call-site count)
- Security/correctness sensitivity (heuristics: name/path matches `auth|crypto|password|token|payment|parse|sanitize`)
- Recent change frequency (git log churn)
- Presence of explicit error paths (`raise`/`throw`/error returns)

High-priority symbols get analyzed first. Low-priority symbols stay in the index and are picked up on subsequent runs.

### 4. Analyze each prioritized symbol

For each symbol on the work list, the agent does this per-symbol pass:

**4a. Infer the specification.** Read signature, types, body, docstring, name. Write one sentence: "this function is supposed to ___."

**4b. Enumerate input equivalence classes.** Walk the **edge-case taxonomy** (see `edge-case-taxonomy.md`). Do not free-associate — apply the checklist explicitly. For each category, ask: does an instance of this category exist for this function's inputs? Record only the ones that apply.

**4c. Enumerate expected behaviors.** Returns, raises, side effects, state changes. Every `raise`/`throw`/error return in the body is a behavior cell. Every distinct return type or shape is a cell.

**4d. For classes, add dimensions.** Methods get analyzed individually with `self` state as an extra input dimension. Additionally, the class as a whole gets:
- **Invariants** — properties that must hold across method calls (push/pop round-trip, open/close pairing)
- **State transitions** — if stateful, the state machine (e.g., `Connection`: closed → open → closed); calling each method in each state is a cell
- **Construction** — invalid args, defaults
- **Lifecycle** — destructors, context managers, cleanup-on-error

Trivial data classes (records, dataclasses with no logic) need only minimal coverage: equality, hashing, serialization round-trip if applicable.

**4e. Build the behavior matrix.** A list of cells: `(input_class, expected_behavior)`.

**4f. Map existing tests onto cells.** Find tests that call this symbol (grep imports/calls). For each candidate test, read its body and judge:

- Does the input it passes belong to a specific cell's input class?
- Is the assertion meaningful? (Not `assert result is not None`, not bare `result`, not a tautology.) The assertion must actually verify the expected behavior.
- A weak assertion does **not** cover a cell. Record the cell as a gap and note the weak test.

**4g. Classify each cell.**
- **covered** — at least one test exercises the input class with a meaningful assertion
- **gap** — no test, or only tests with weak/wrong assertions
- **unspecified** — the function's behavior on this input is genuinely ambiguous from the code/docs; surface this for human clarification rather than guessing

**4h. Write the analysis entry** to `analysis.json` with spec, behavior matrix, status per cell, covering tests, and timestamp.

### 5. Optional — mutation testing as empirical validation

Run `scripts/run_mutation.py <symbol>` to dispatch the appropriate per-language mutation tool (mutmut/Stryker/PIT/cargo-mutants/etc.). It injects small bugs and re-runs the test suite. Surviving mutants = tests touch code but don't verify it.

Attach `mutation_results` to the analysis entry. If you marked cells as covered but mutants survive, your assessment is wrong — investigate.

### 6. Report

Run `scripts/report.py <target_dir>` to render a human-readable gap report from `analysis.json`. Sample output per symbol:

```
function: parse_date(s: str) -> date
spec: parses ISO-8601 date strings; raises ValueError on malformed input
behavior matrix:
  ✓ valid ISO date → date object         [covered: test_parse_basic]
  ✓ leap year Feb 29                     [covered: test_leap_year]
  ✗ empty string → ValueError            [GAP]
  ✗ malformed input → ValueError         [GAP — only ":::" tested, not other shapes]
  ✗ timezone-aware string                [GAP]
  ? whitespace-padded input              [UNSPECIFIED — clarify intent]
mutation: 2/16 mutants survived (mutmut)
```

## Test generation is out of scope

This skill produces a gap report. Generating actual test code for identified gaps is a follow-up AI conversation seeded with the report — not part of this skill. Keep the skill focused.

## Common mistakes

| Mistake | Reality |
|---|---|
| Trusting test names | `test_empty_string` may not actually pass `""`. Read the body. |
| Accepting weak assertions | `assert result is not None` covers nothing. Require assertions that pin behavior. |
| Free-associating edge cases | LLMs miss categories inconsistently. Walk the taxonomy explicitly. |
| Treating all inputs as one class | A function taking `list[int]` has many classes: empty, single, sorted, reverse-sorted, duplicates, negatives. Each is a cell. |
| Forgetting error paths | Every `raise` is a cell. If no test triggers it, it's a gap. |
| Skipping classes' state machine | Stateful classes have transitions, not just methods. A method call is a cell *per starting state*. |
| Confidently filling "unspecified" | If the spec is genuinely ambiguous, mark `?` and surface to the human. Don't invent the contract. |
| Re-analyzing unchanged code | Trust the body-hash invalidation. Don't re-run unchanged entries. |

## Triage tips

- First run on a new codebase: triage hard, analyze only `high` priority. Build out the index over subsequent runs.
- On large codebases (>1000 functions) it is correct to leave most of the index unanalyzed for a long time.
- Re-triage when many files change (e.g., after a refactor) because complexity scores may have shifted.

## File reference

- `edge-case-taxonomy.md` — the categorical checklist applied at step 4b
- `scripts/build_index.py` — tree-sitter symbol discovery
- `scripts/find_stale.py` — git-diff + hash-based invalidation
- `scripts/triage.py` — risk scoring → priority list
- `scripts/run_mutation.py` — per-language mutation tool dispatcher
- `scripts/report.py` — render `analysis.json` to readable report

## Related skills

- `requirements-coverage-analysis` — complementary skill for product-level coverage (requirements doc → integration tests). Behavioral coverage catches code bugs; requirements coverage catches "we built the wrong thing." Use both.

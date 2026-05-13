# Behavioral Coverage Analysis — Skill Design Plan

**Date:** 2026-05-13
**Goal:** Build an AI-enabled code coverage skill that measures *behavioral* (specification) coverage instead of execution coverage, and a companion skill for requirements-based integration coverage.

## Problem statement

Traditional coverage tools (line/branch coverage) measure whether tests *executed* code. They say nothing about whether tests *meaningfully verify* behavior. You can hit 100% line coverage with `assert True`. We want **behavioral coverage**: for each function/class, did the test suite exercise the meaningful equivalence classes of input → output behavior, including edge cases and error paths?

## Core concept

Per function/method:

1. **Infer the specification** from signature, types, body, docstring, name.
2. **Enumerate the input space** as equivalence classes (not infinite values — categories that should behave the same).
3. **Enumerate expected outputs / behaviors** including returns, raises, side effects.
4. **Build the behavior matrix** (input class × expected behavior).
5. **Map existing tests onto the matrix** — read test bodies, verify assertions are meaningful (not just present).
6. **Classify each cell:** covered / gap / unspecified.
7. **Report gaps** with concrete suggested test cases.

The hard intellectual work is steps 2–3. Tooling handles the bookkeeping.

## Two separate skills

### Skill 1: `behavioral-coverage-analysis`
Code-level coverage. Function/class → behavior matrix → gap report.

### Skill 2: `requirements-coverage-analysis`
Product-level coverage. Requirements doc → integration test traceability matrix → gap report.

They are complementary: one catches code bugs, the other catches "we built the wrong thing."

## Edge-case taxonomy (checklist applied to every function)

Without an explicit checklist an LLM will miss categories inconsistently. The skill ships with a taxonomy file:

- **Boundary values:** 0, 1, -1, max, min, off-by-one
- **Empty / degenerate:** `""`, `[]`, `{}`, `None`/`null`, single-element
- **Type variants** (dynamic langs): wrong types, subclasses, duck-typed
- **Invalid inputs:** out-of-domain, malformed structures
- **Boundary structural:** very large, very small, deeply nested, recursive
- **Numerical:** NaN, Inf, -0, float precision, overflow/underflow
- **String:** unicode, whitespace-only, very long, escape chars, encoding
- **Collection:** duplicates, ordering, mutation during iteration
- **Concurrency:** reentrance, races (where applicable)
- **State / side effects:** idempotency, ordering, failure mid-operation
- **Error paths:** every `raise`/`throw`/error return must have a test

## Class and data-structure analysis

Same intellectual move, more dimensions:

- **Each method:** analyze like a function, with `self` state as additional input dimension
- **Invariants:** properties that hold across method calls (push/pop, open/close)
- **State transitions:** state machine cells (e.g., closed → open → closed; calling `send()` on closed)
- **Construction:** invalid constructor args, defaults
- **Lifecycle:** destructors, context managers, cleanup on error
- **Trivial data classes:** minimal coverage (equality, hashing, serialization round-trip)

## Triage

Real codebases have thousands of functions; most are trivial. Triage before deep analysis. Risk signals:

- Cyclomatic complexity (branch count)
- Public API surface (call-site count)
- Security/correctness sensitivity (auth, crypto, money, parsing untrusted input)
- Recent change frequency (hotspots are bug-prone)
- Functions with `raise`/error paths

**Important:** the *index* always contains every function. Triage produces a *priority list* for analysis order. Lower-priority entries are filled in over subsequent runs.

## Caching architecture

Cache lives in **`<target_dir>/.coverage_cache/`** — root of whatever directory the user points the skill at.

```
.coverage_cache/
  index.json       # every function/class/method discovered
  analysis.json    # behavior matrices, gaps, test mappings
  meta.json        # last commit, last run timestamp, tool versions
```

### Index entry shape
```json
{
  "src/parser.py::parse_date": {
    "kind": "function",
    "signature": "parse_date(s: str) -> date",
    "signature_hash": "abc123",
    "body_hash": "def456",
    "language": "python",
    "loc": {"file": "src/parser.py", "start": 42, "end": 87},
    "complexity": 7,
    "has_error_paths": true,
    "priority": "high",
    "last_analyzed": "2026-05-13T08:20:00Z",
    "last_commit": "21eda87"
  }
}
```

### Analysis entry shape
```json
{
  "src/parser.py::parse_date": {
    "spec": "parses ISO-8601 date strings; raises ValueError on malformed input",
    "behavior_matrix": [
      {"id": "valid_iso", "input_class": "valid ISO date string", "expected": "date object", "status": "covered", "tests": ["tests/test_parser.py::test_parse_basic"]},
      {"id": "leap_year", "input_class": "Feb 29 leap year", "expected": "date object", "status": "covered", "tests": ["tests/test_parser.py::test_leap_year"]},
      {"id": "empty", "input_class": "empty string", "expected": "ValueError", "status": "gap", "tests": []},
      {"id": "tz_aware", "input_class": "timezone-aware string", "expected": "unspecified", "status": "unspecified", "tests": []}
    ],
    "mutation_results": {"survived": 2, "killed": 14, "tool": "mutmut"}
  }
}
```

### Invalidation
Re-analyze a function when:
- `body_hash` changes (compared against cache)
- Any test that claims to cover it changes (`body_hash` of test changes)
- Optional: dependencies change

### Git-driven incremental updates
`git log --name-only $LAST_RUN_COMMIT..HEAD` → list of changed files → tree-sitter re-parses only those → body-hash check decides what actually needs re-analysis.

## Discovery: tree-sitter, not VS Code

Tree-sitter is the right tool for "all languages, CLI, no editor":
- Language-agnostic with one library (~all major langs have grammars)
- Runs in CI, no editor dependency
- Produces ASTs for walking to extract functions, classes, methods
- Python bindings: `tree-sitter` + `tree-sitter-languages`

## Mutation testing (validation layer)

A mutation tester injects small bugs ("mutants") — flip `>` to `>=`, change `+` to `-`, replace `True` with `False` — then runs your tests. Surviving mutants = tests touch code but don't verify it.

**Use as empirical validation** of AI-judged coverage. If we say a function is well-covered but mutants survive, our assessment is wrong.

Per-language tool dispatch:
- Python → mutmut or cosmic-ray
- JS/TS/C# → Stryker
- Java → PIT
- Rust → cargo-mutants
- Go → gremlins, go-mutesting
- Ruby → mutant
- PHP → infection

Optional step; recorded into `mutation_results` on the analysis entry.

## Skill 1 file layout

```
skills/behavioral-coverage-analysis/
  SKILL.md
  edge-case-taxonomy.md          # the long checklist
  scripts/
    build_index.py               # tree-sitter symbol discovery
    find_stale.py                # git-diff invalidation
    triage.py                    # priority scoring
    report.py                    # render gap report
    run_mutation.py              # per-language mutation tool dispatch
```

## Skill 2 file layout

```
skills/requirements-coverage-analysis/
  SKILL.md
```

Requirements coverage maps a requirements doc (PRD, spec, user stories) → integration tests. Different unit (requirement, not function), different test type (integration/e2e, not unit), different question ("does the product do what we promised?"). No tree-sitter needed; reads markdown/yaml/structured requirements and greps tests for traceability markers (e.g., `@req(R-014)`).

## Output format

Human-readable gap report per function:

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

The `?` (unspecified) category matters: when the spec is genuinely ambiguous, the right output is "ask the human", not "write a test".

## Process flow (skill execution)

1. **Index** — `build_index.py <target_dir>`: tree-sitter walks every source file, writes `index.json` with every function/class/method.
2. **Stale check** — `find_stale.py`: compares `index.json` body hashes against current source + git history; emits list of symbols needing (re)analysis.
3. **Triage** — `triage.py`: scores symbols by risk; emits priority-ordered work list.
4. **Analyze** — for each prioritized symbol the agent: infers spec → walks edge-case taxonomy → builds behavior matrix → finds covering tests → verifies assertion quality → classifies each cell. Writes `analysis.json` entry.
5. **(Optional) Mutate** — `run_mutation.py <symbol>`: dispatches per-language mutation tool, attaches results to analysis entry.
6. **Report** — `report.py`: renders human-readable gap report from `analysis.json`.

Lower-priority symbols are picked up on subsequent runs incrementally.

## Test generation: out of scope for the skill itself

The skill produces a gap report. Generating actual test code for identified gaps is a follow-up AI conversation seeded with the report — not built into the skill. Keeps the skill focused.

## Open decisions resolved

| Question | Decision |
|---|---|
| CLI vs editor-bound | CLI via tree-sitter |
| Language scope | All — general taxonomy |
| Cache location | `<target_dir>/.coverage_cache/` |
| Class coverage | In scope; methods + invariants + state transitions |
| Requirements coverage | Separate skill |
| Mutation testing | Integrated, optional validation step |
| Triage | Built-in section of the skill |
| Test stub generation | Out of scope (follow-up AI thread) |
| Index completeness | Always full; triage only orders work |

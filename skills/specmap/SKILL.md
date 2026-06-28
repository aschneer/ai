---
name: specmap
description: Only use when explicitly invoked as /specmap. Audits whether a codebase delivers what a PRD or spec promised and produces a traceability matrix mapping requirements to tests.
disable-model-invocation: true
---

# Specmap

## Overview

`testmap` asks "does each function handle all its inputs?" — this skill asks a different question: **"does the product do what we promised?"** Given a requirements document (PRD, spec, user stories, acceptance criteria) and a codebase, produce a traceability matrix mapping each requirement to the integration/end-to-end tests that verify it, and report which requirements are unverified.

This skill is **complementary** to behavioral coverage:

| | Behavioral coverage | Requirements coverage (this skill) |
|---|---|---|
| Input | Source code | Requirements document |
| Unit | Function / class | Requirement / user story |
| Test type | Unit tests | Integration / end-to-end / acceptance tests |
| Question | "Does the code handle all its inputs?" | "Does the product do what we promised?" |
| Output | Behavior matrix per function | Traceability matrix per requirement |
| Catches | Code-level bugs | "We built the wrong thing" |

Use both. They catch different classes of problem.

## When to use

- Auditing a release against its PRD before shipping
- Compliance/regulated environments where requirement traceability is mandatory (medical, aviation, finance)
- Reviewing whether every user story has at least one acceptance test
- Onboarding to an existing codebase to understand which requirements are actually verified
- Closing a project — what did we build, what did we promise, where's the gap?

## When NOT to use

- No formal requirements document exists (use `testmap` instead)
- Pure library/framework code with no product requirements
- Throwaway prototypes
- When the requirements doc is so stale it no longer reflects intent (rewrite it first)

## Inputs

- A **target directory** (codebase root; cache lives in `<target_dir>/.coverage_cache/`)
- A **requirements document** — markdown, yaml, json, or structured text. Each requirement needs a stable identifier (e.g., `R-014`, `US-027`, `AC-3.2.1`).

If the requirements doc has no IDs, the first step is to **add them**. Coverage without stable IDs cannot be tracked across runs.

## Cache layout

Shares the cache directory with `testmap`:

```
.coverage_cache/
  requirements.json   # parsed requirements with stable IDs
  req_coverage.json   # requirement → tests mapping, gap status
  meta.json           # last analyzed timestamp, source doc hash
```

## Process

### 1. Parse and ID the requirements

Read the requirements document. Extract each atomic requirement — one testable assertion per entry. If IDs are missing, propose them and write back to the doc (e.g., insert `[R-001]` markers).

A good requirement is:
- **Atomic** — one verifiable behavior, not a paragraph of related ones
- **Testable** — describes observable behavior, not implementation
- **Identified** — has a stable ID that survives rewording

Decompose compound requirements: "users can log in via email or SSO" → `R-014a: email login`, `R-014b: SSO login`.

Write the parsed list to `requirements.json`:

```json
{
  "R-014a": {
    "text": "Users can log in with email + password",
    "section": "Authentication",
    "priority": "must",
    "source_doc": "docs/PRD.md",
    "source_line": 142
  }
}
```

### 2. Find candidate tests

Look in the codebase for integration / end-to-end / acceptance tests. Heuristics:

- Test files in directories named `integration/`, `e2e/`, `acceptance/`, `features/`, `cypress/`, `playwright/`
- Test names matching `test_*_flow`, `test_*_e2e`, `scenario_*`
- BDD specs (`.feature` files with Gherkin)
- Test files that exercise the public API surface rather than internal functions

Unit tests usually don't count — they verify code, not product requirements. (Exception: a unit test of the highest-level orchestration function may verify a requirement directly.)

### 3. Map tests to requirements

Two mapping mechanisms, used together:

**a. Explicit markers.** Convention: tests tag the requirements they verify:

```python
@req("R-014a")
def test_email_login_happy_path(): ...

# or in BDD:
@R-014a
Scenario: User logs in with email
```

Explicit markers are authoritative and survive renaming.

**b. Inferred mapping.** For unmarked tests, infer the requirement by matching test name + body against requirement text (LLM judgment). Mark these as `inferred` so a human can confirm.

### 4. Verify the test actually verifies

For each (requirement, test) pair, read the test body and judge:

- Does it actually exercise the behavior the requirement describes? (Not just the code path — the end-to-end behavior.)
- Are the assertions meaningful? (Same standard as behavioral coverage — no `assert response is not None` for "user receives confirmation email".)
- Does it cover the happy path, or also failure modes the requirement implies?

A weak or partial test does **not** count as covering the requirement. Mark a gap.

### 5. Classify each requirement

- **covered** — at least one strong test, explicitly marked or confidently inferred, verifies the requirement end-to-end
- **partial** — tests exist but cover only some failure modes / preconditions / alternative flows
- **gap** — no test verifies this requirement
- **untestable-as-stated** — the requirement is not falsifiable as written (vague, subjective, or describes a non-behavior). Surface to the human to rewrite.

### 6. Write `req_coverage.json`

```json
{
  "R-014a": {
    "status": "covered",
    "tests": [
      {"path": "tests/e2e/test_auth.py::test_email_login_happy_path", "match": "explicit", "verifies": "happy path"},
      {"path": "tests/e2e/test_auth.py::test_email_login_bad_password", "match": "explicit", "verifies": "wrong password rejected"}
    ],
    "missing_aspects": []
  },
  "R-022": {
    "status": "gap",
    "tests": [],
    "missing_aspects": ["no integration test for password reset email flow"]
  }
}
```

### 7. Report

Produce a traceability matrix. Sample:

```
REQUIREMENT COVERAGE — docs/PRD.md @ 2026-05-13

✓ R-001    User signup with email                          [test_signup_happy_path, test_signup_duplicate]
✓ R-014a   Email + password login                          [test_email_login_*]
~ R-014b   SSO login                                       [test_sso_redirect — missing: callback failure case]
✗ R-022    Password reset email flow                       [GAP]
✗ R-031    Audit log of all admin actions                  [GAP]
? R-040    "System should be responsive"                   [UNTESTABLE AS STATED — rewrite]

Summary: 12/18 covered (66.7%), 2 partial, 3 gaps, 1 untestable
```

## Common mistakes

| Mistake | Reality |
|---|---|
| Requirements without IDs | Coverage can't be tracked across runs; reorder/reword breaks the link. Add stable IDs first. |
| Counting unit tests as covering requirements | Unit tests verify code, not product behavior. A green unit test doesn't mean the user-facing requirement works. |
| Compound requirements counted as one | "Login via email or SSO" is two requirements. Split them. |
| Trusting test names | `test_login` may not actually log in end-to-end. Read the body. |
| Inferring matches confidently | Inferred mappings are guesses. Mark them `inferred` and require human review. |
| Skipping the "verify the test verifies" step | A weak test is worse than no test — it provides false confidence. |
| Treating vague requirements as testable | "System should be fast" is not falsifiable. Mark untestable and push back to the spec author. |

## Tools

This skill is primarily judgment work and is light on tooling. The simplest implementation uses grep:

```bash
# find explicit markers in tests
grep -rn '@req("R-' tests/
grep -rn '^@R-[0-9]' features/

# find untagged integration tests
find tests/integration tests/e2e -name 'test_*.py' -o -name '*.feature' 2>/dev/null
```

A more thorough implementation parses the requirements doc and tests programmatically; the cache layout above supports either approach.

## Related skills

- `testmap` — complementary code-level coverage. Use both: this skill catches missing requirements, that one catches missing edge cases inside the code that implements them.

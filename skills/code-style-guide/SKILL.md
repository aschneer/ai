---
name: code-style-guide
description: >-
  Apply clean-code standards when writing, refactoring, or reviewing code in any
  language. Use whenever the user asks you to write new code, improve readability,
  refactor, do a code review, fix code smells, name things better, reduce complexity,
  organize imports, or follow team coding conventions — even if they do not say "style
  guide". Also use when editing Python, C++, or Go and language-specific conventions
  matter. Triggers: "clean code", "code review", "refactor", "naming", "code smells",
  "DRY", "single responsibility", "reduce nesting", "organize imports", "style guide",
  "best practices", "readable code", "maintainable code".
---

# Code Style Guide

If this skill is invoked, read `references/index.md` first, then load only the reference files relevant to the task. Do not load every file by default — progressive disclosure keeps context focused.

**Minimum for most coding tasks:** `core_principles.md`, `organization.md`, and the language file if known (`python.md`, `cpp.md`, or `go.md`).

**Add by task:** `code_smells.md` (refactors/reviews), `testing.md` (tests), `code_review.md` (formal review), `security.md` (auth/input/DB), `performance.md` (optimization), `formatting.md`, `documentation.md`, `version_control.md`, `best_practices.md`.

These standards apply to **new code you write**, **refactors you perform**, and **reviews you give**. They are defaults — when the target codebase already has an established pattern, match the codebase first and note any intentional deviation.

## How to apply

### Writing new code

1. **Match the codebase** — scan nearby files for naming, import layout, error-handling patterns, and file structure before adding code.
2. **Start simple** — smallest correct solution; no speculative abstraction (YAGNI).
3. **Design in layers** — high-level functions first, helpers below; one responsibility and one abstraction level per function.
4. **Name for the reader** — intention-revealing names so comments rarely need to explain *what*.
5. **Guard early** — validate inputs and handle edge cases with early returns; keep nesting ≤ 3 levels.
6. **Format with tooling** — use the project's formatters (Black/isort, clang-format, gofmt/goimports) rather than hand-aligning.

### Refactoring existing code

1. Identify code smells from `references/code_smells.md` (long functions, deep nesting, duplication, magic numbers, etc.).
2. Extract or rename in small steps; preserve behavior.
3. Remove dead code, commented-out blocks, and unused imports.
4. Leave the file cleaner than you found it (Boy Scout Rule).

### Code review

When reviewing, check against the **Review checklist** below and use the detailed prompts in `references/code_review.md`. Cite specific lines and suggest concrete fixes — not vague "could be cleaner" feedback.

## Review checklist

Use this as a structured pass; details and rationale live in the reference files listed in `references/index.md`.

| Area | Check | Reference |
|------|-------|-----------|
| Functions | Single responsibility; ≤ ~30 lines when practical; ≤ 4 parameters; one abstraction level | `core_principles.md` |
| Classes | Methods operate on class state; small and focused; composition over inheritance | `core_principles.md` |
| Naming | Intention-revealing; consistent with codebase; booleans read as predicates | `core_principles.md` |
| Complexity | Nesting ≤ 3; cyclomatic complexity < 10; complex conditionals extracted or named | `core_principles.md` |
| Duplication | Repeated logic extracted; DRY without premature abstraction | `core_principles.md` |
| Comments | Explain *why*, not *what*; no commented-out code | `core_principles.md` |
| Imports | Top of file; three sections (stdlib → third-party → local); alphabetical; one per line | `organization.md` |
| Errors | Handled at the right level; context preserved; inputs validated early; never swallowed | `organization.md` |
| Tests | Public behavior covered; Arrange-Act-Assert; descriptive test names; edge cases | `testing.md` |
| Security | Input validation; no secrets in logs; parameterized queries | `security.md` |
| Performance | Clarity first; optimize only with evidence (profile) | `performance.md` |

## Import layout (non-negotiable default)

Unless the codebase documents an exception — full rules in `references/organization.md`:

1. All imports at the top of the file (after module docstring if present).
2. Three sections separated by blank lines: **standard library → third-party → local**.
3. Alphabetical within each section; one import per line.
4. Remove unused imports.

Document inline only when a circular-import or lazy-load constraint truly requires a non-top import.

## Language-specific rules

| Language | Reference |
|----------|-----------|
| Python | `references/python.md` |
| C++ | `references/cpp.md` |
| Go | `references/go.md` |

For other languages, follow the universal references and existing project conventions.

## When NOT to use

- User explicitly asks to ignore style or match a different style guide for this task.
- Generated or vendored third-party code that should not be reformatted.
- One-line or trivial edits where raising style issues would be noise — still follow import and naming rules on touched lines.

## Output expectations

- **Writing code**: produce code that already conforms; do not narrate every rule unless the user asked for explanation.
- **Reviewing**: lead with findings grouped by severity; include file/line references and suggested rewrites.
- **Refactoring**: describe what smell you fixed and why the new shape is clearer.

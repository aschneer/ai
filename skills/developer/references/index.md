# Reference Index

Read only the files relevant to the task. Universal standards apply to all languages; language files add conventions on top.

## Universal (read for most tasks)

| File | Topics |
|------|--------|
| `core_principles.md` | Functions, classes, naming, complexity, DRY |
| `code_smells.md` | Warning signs to flag in review or refactor |
| `organization.md` | Imports, file/directory naming, libraries vs entry points, file structure, errors, function order |
| `best_practices.md` | YAGNI, readability, extraction heuristics, Boy Scout Rule |

## Task-specific

| File | When to read |
|------|--------------|
| `testing.md` | Test file naming, writing and reviewing tests |
| `code_review.md` | Performing a structured code review |
| `formatting.md` | Setting up or enforcing formatters |
| `performance.md` | Performance-sensitive code or optimization discussions |
| `security.md` | Input handling, auth, data access, logging |
| `version_control.md` | Commits, branches, merge workflow |
| `documentation.md` | READMEs, API docs, ADRs |

## Language-specific

| File | When to read |
|------|--------------|
| `python.md` | Python source or tests |
| `cpp.md` | C++ source or headers |
| `go.md` | Go source |

## Getting started

**Most coding tasks:** `core_principles.md`, `organization.md`, and the language file if known.

**Also load when relevant:** `code_smells.md` and `best_practices.md` (refactors), `code_review.md` (reviews), plus any task-specific files from the tables below.

For a full review of new code in a known language, read the universal files above, the language file, and any task-specific files that apply (e.g. `testing.md` if tests changed).

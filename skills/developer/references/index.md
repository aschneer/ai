# Reference Index

Read only the files relevant to the task. Universal standards apply to all languages; language files add conventions on top.

## Universal (read for most tasks)

| File | Topics |
|------|--------|
| `core_principles.md` | Functions, classes, naming, complexity, DRY |
| `code_smells.md` | Warning signs to flag in review or refactor |
| `organization.md` | Imports, file structure, errors, function order |
| `best_practices.md` | YAGNI, readability, extraction heuristics, Boy Scout Rule |

## Task-specific

| File | When to read |
|------|--------------|
| `testing.md` | Writing or reviewing tests |
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

For a full review of new code in a known language, read `core_principles.md`, `organization.md`, the language file, and any task-specific files that apply (e.g. `testing.md` if tests changed).

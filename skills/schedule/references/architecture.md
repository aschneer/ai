# Architecture

How the Schedule skill separates validation from computation. Read this before changing library code or adding new rules.

## Principle: validate first, compute on clean input

The scheduling engine uses two layers:

| Layer | Module | Purpose | On failure |
|-------|--------|---------|------------|
| **Structural** | `validate_lib.py` | JSON Schema — shape, required/forbidden fields, kinds | List every schema error; stop |
| **Logical** | `logic_validate_lib.py` | Rules schema cannot express — unique IDs, predecessor refs, cycles, listing rules, milestone working days | List every logic error; stop |
| **Compute** | `compute_lib.py` | CPM forward pass on validated input | Assumes input is valid; no warnings channel |

**Compute does not paper over bad data.** If the schedule violates a rule, validation fails and compute is not run. The agent (or user) fixes the YAML and re-runs.

This keeps compute code small and deterministic: no duplicate-ID handling, no unknown-predecessor skips, no milestone non-working-day workarounds, no post-hoc “unscheduled item” warnings for cycles.

## Error reporting

Validation collects **all** errors before returning — not just the first. Each distinct problem gets its own message. Each duplicate ID produces one error per pair (first occurrence vs duplicate). The agent reads the full list, fixes the schedule file, and runs validate again.

Example messages:

```
schedule: items: duplicate id 1: 'First' and 'Duplicate'
schedule: item 5: predecessor 99: unknown task id
schedule: milestone 13: date 2026-06-20 falls on a non-working day
schedule: cyclic predecessor dependency: 1 → 2 → 1
schedule: item 20: must not include 0FS when other predecessors are listed
```

## Agent boundaries

| Edit | Do not edit |
|------|-------------|
| Schedule and calendar YAML in the **user's project directory** | `skills/schedule/` library code, schemas, tests, or SKILL.md |

When `schedule-validate` or `schedule-compute` fails, fix the **schedule file** — never patch the skill to bypass a validation rule.

When the agent fixes validation errors, it must **list every error and its planned YAML fix for the user before editing** (unless the user already asked it to fix the file). The library never writes schedule files; only the agent does, and the user should see the plan first.

## Why not Pydantic?

Schedule and calendar files are validated with **JSON Schema** (`schemas/*.schema.yaml`) via `jsonschema`. The same schemas validate in the editor (Red Hat YAML) and at runtime. Logical rules live in Python because they need the calendar, graph walks, and cross-field checks JSON Schema cannot express cleanly.

We do not maintain a second model layer (e.g. Pydantic) to avoid drift and extra dependencies.

## Module layout

```
src/schedule/
  validate_lib.py       # JSON Schema
  logic_validate_lib.py # Semantic / graph rules
  io_lib.py             # Load YAML, run both validation layers
  compute_lib.py        # CPM only
  calendar_lib.py       # Working-day math
  predecessors_lib.py   # Parse predecessor strings
```

CLIs (`schedule-validate`, `schedule-compute`) load through `io_lib.load_schedule_project()`, which runs structural + logical validation before compute.

## Adding a new rule

1. Decide: structural (schema) or logical (Python)?
2. If logical, add a check to `logic_validate_lib.py` with a clear error message.
3. Document the rule in `data_model.md` or `prd.md`.
4. Add a test in `tests/test_logic_validate_lib.py`.
5. Do **not** add defensive handling in `compute_lib.py` — compute should remain unaware.

## Related references

- `scheduling_algorithm.md` — CPM steps (runs only after validation passes)
- `data_model.md` — editing rules the validator enforces
- `context.md` — domain glossary

---
name: schedule
description: Text-native Microsoft Project Auto Schedule alternative using YAML schedule files and deterministic CPM calculation. Use whenever the user mentions project schedules, Gantt charts, task dependencies, predecessors, milestones, critical path, MS Project-style planning, landscaping/construction/renovation timelines, or wants to create, edit, or visualize a schedule without a traditional PM app — even if they do not say "schedule file" or name this skill.
---

# Schedule

If this skill is invoked, apply every standard below in full.

A text-native alternative to Microsoft Project Auto Schedule. The schedule lives in YAML files the user and agent edit. **Library code calculates dates (CPM); the agent never does date math.**

## Core split

| Agent | Library code |
|-------|----------------|
| Edit schedule and calendar YAML in the **user's project** | Validate against JSON Schema and logic rules |
| Ask user for schedule/project path | CPM schedule calculation |
| Add tasks, groups, milestones, predecessors | Working-day calendar math |
| Assign stable Unique IDs | Render static HTML Gantt |
| Fix validation errors in the schedule file | Report all validation errors at once |

Scheduling code is **read-only** — it validates and computes. It reads schedule and calendar files but **never writes or back-modifies** them. Only the agent (or user) edits `schedule.yaml` and `calendar.yaml`.

**Do not modify skill code.** The agent edits the user's schedule and calendar YAML only. Never change `skills/schedule/` (library code, schemas, tests, SKILL.md) unless the user explicitly asks to change the skill itself. When validation or compute fails, fix the **schedule file** — not the tool.

Before adding library code for a new capability, ask: *can the skill instruct the agent to do this instead?* Prefer code only where correctness requires it.

## Project directory

Each schedule lives in one folder:

```
my-renovation/
  schedule.yaml    # any filename
  calendar.yaml    # path relative to schedule file
  gantt.html       # generated output
```

The schedule filename is not fixed. Ask the user for the **schedule file path** or **project directory** if not provided.

## Workflow

### 1. Locate the project

If the user gives a directory, find the schedule YAML (ask if multiple). If they give a file path, use its parent as the project directory.

Read `references/context.md` before editing — it defines domain terms. Read `references/data_model.md` when creating or structurally changing items. Read `references/architecture.md` for how validation and compute fit together.

### 2. Edit the schedule (agent)

Edit YAML directly. Rules that matter most:

**Three kinds** — `kind` is always the **first field** on every item:

| Kind | Key fields | Forbidden |
|------|------------|-----------|
| `milestone` | `date` (user-set, must be a working day) | `duration`, `predecessors`, `children` |
| `task` | `duration`, `predecessors` | `date`, `children` |
| `group` | `predecessors`, `children` (min 1) | `date`, `duration` |

**ID 0** is reserved for the project start milestone. IDs are stable and **must be unique** — never renumber when reordering items.

**Predecessors** — inline list of MS Project strings only:

```yaml
predecessors: ["0FS"]
predecessors: ["5FS", "7SS+2d"]
predecessors: ["10SS"]
```

Listing rules:
- Only **immediate** predecessors — not the full transitive chain
- Top-level item with no other preds → `["0FS"]` only
- Child with no other preds → `["{parentId}SS"]` only
- Otherwise list specific preds — **never** mix in `0FS`
- Milestones cannot have predecessors
- No cyclic predecessor dependencies

**Durations and lag:** days and weeks only (`4d`, `2w`). No hours.

**Task order:** controlled by user and agent. Scheduling code does not rewrite file order. Convention: parent group above its children; siblings by computed start date when practical.

**Milestones** are the only user-defined date constraints. Their `date` is authoritative and must fall on a working day in the calendar file.

### 3. Run the toolchain (library)

Run from `skills/schedule/` (uv project — run `uv sync` once to install dependencies):

```bash
cd skills/schedule
uv sync

# Validate schedule + calendar (JSON Schema + logic rules)
uv run validate <schedule-file>

# Compute, write gantt_data.json, deploy Gantt viewer, print JSON, serve locally
uv run compute <schedule-file>

# Non-default: file only, no terminal JSON, no server
uv run compute <schedule-file> --no-stdout --no-serve
```

**`compute`** validates, runs CPM, writes **`gantt_data.json`**, copies **`gantt.html`** and **`gantt.js`** into the project directory, prints JSON to stdout (default), and starts a dev server (default). It prints **local** and **network** Gantt URLs — use whichever opens from your machine (see `references/decisions.md`). Use **`--no-serve`** for CI or when you only need the files.

When validation fails, read **all** error messages. Do not patch the skill library to bypass a rule.

**Before editing YAML to fix validation errors**, present to the user:

1. **Every validation error** — quote or list each message from the tool output
2. **Planned fix for each** — what you will change in the schedule or calendar file and why

Wait for the user to confirm (or proceed if they already asked you to fix it). Then edit the schedule/calendar YAML, re-run validate, and repeat until clean.

The library never writes these fixes for you — that is always the agent's job, and the user should see the plan first.

### 4. Report results (agent)

Present computed dates (from JSON or stdout), call out critical items (`is_critical: true`), and the Gantt URLs printed by `compute` when serving.

If validation failed and you have not yet fixed the file: list every error and your planned YAML changes — do not edit until the user has seen the plan (unless they already asked you to fix it).

Do not fix validation problems by writing computed `start`/`finish` dates onto non-milestone items — only milestones have user-set dates.

## When NOT to use

- User wants interactive Gantt drag-and-drop editing
- User wants manual fixed dates on every task (out of scope for MVP)
- User wants resource leveling, cost tracking, or cross-project links

## References

- `references/context.md` — domain glossary (read before editing)
- `references/architecture.md` — validate-first design, module layout, implementation
- `references/prd.md` — product requirements and schedule file format (hard requirements)
- `references/data_model.md` — YAML examples and editing cheat sheet
- `references/decisions.md` — architecture decisions (ADR-style) and resolved product decisions
- `schemas/` — JSON Schema files **written in YAML** (e.g. `schedule.schema.yaml`, `calendar.schema.yaml`). JSON Schema is the validation standard; YAML is the authoring format. The same schema validates schedule data files in the editor (Red Hat YAML + `yaml.schemas`) and in library code.

## Adding library code

Python code lives in `src/schedule/`. Library modules use the `_lib.py` suffix (e.g. `validate_lib.py`, `io_lib.py`). Runnable entry points (`validate.py`, `compute.py`) live in the same package and are exposed as uv commands (`validate`, `compute`). Static Gantt assets live in `src/schedule/assets/`. Tests live in `tests/`. Dependencies are managed with **uv** — `pyproject.toml` and `uv.lock` in this skill directory.

New code must be modular and composable:

- One capability per module (parse predecessors, validate, CPM forward pass, calendar, render)
- Modules callable independently
- Unit-testable in isolation
- Thin scripts compose modules; the agent may also compose them step by step

Full specification: `references/prd.md` (product) and `references/architecture.md` (implementation).

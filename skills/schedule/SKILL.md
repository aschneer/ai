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
| Edit schedule and calendar YAML | Validate against JSON Schema (authored in YAML) |
| Ask user for schedule/project path | CPM schedule calculation |
| Add tasks, groups, milestones, predecessors | Working-day calendar math |
| Assign stable Unique IDs | Render static HTML Gantt |
| Interpret warnings, suggest fixes | Detect schedule logic problems |

Scheduling code is **read-only** — it validates, computes, and warns. It never modifies schedule or calendar files.

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

Read `references/context.md` before editing — it defines domain terms. Read `references/data_model.md` when creating or structurally changing items.

### 2. Edit the schedule (agent)

Edit YAML directly. Rules that matter most:

**Three kinds** — `kind` is always the **first field** on every item:

| Kind | Key fields | Forbidden |
|------|------------|-----------|
| `milestone` | `date` (user-set) | `duration`, `predecessors`, `children` |
| `task` | `duration`, `predecessors` | `date`, `children` |
| `group` | `predecessors`, `children` (min 1) | `date`, `duration` |

**ID 0** is reserved for the project start milestone. IDs are stable — never renumber when reordering items.

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

**Durations and lag:** days and weeks only (`4d`, `2w`). No hours.

**Task order:** controlled by user and agent. Scheduling code does not rewrite file order. Convention: parent group above its children; siblings by computed start date when practical.

**Milestones** are the only user-defined date constraints. Their `date` is authoritative. Other items reference milestones via predecessor links.

### 3. Run the toolchain (library)

Compose scripts as needed — each module is independently callable:

```bash
# Validate schedule + calendar against JSON Schema (schemas/*.schema.yaml)
python scripts/validate.py <schedule-file>

# Compute dates (CPM); prints JSON to stdout; warns on logic problems
python scripts/compute_schedule.py <schedule-file>

# Generate static HTML Gantt from computed output
python scripts/render_gantt.py <schedule-file> -o gantt.html
```

If scripts are not yet implemented, say so and do not substitute agent arithmetic for schedule calculation.

### 4. Report results (agent)

Present computed dates, critical path, warnings, and Gantt path. Explain warnings in plain language and suggest YAML edits — do not fix by writing dates onto non-milestone items.

## When NOT to use

- User wants interactive Gantt drag-and-drop editing
- User wants manual fixed dates on every task (out of scope for MVP)
- User wants resource leveling, cost tracking, or cross-project links

## References

- `references/context.md` — domain glossary (read before editing)
- `references/data_model.md` — kind constraints, examples, predecessor rules
- `references/prd.md` — full product requirements
- `schemas/` — JSON Schema files **written in YAML** (e.g. `schedule.schema.yaml`, `calendar.schema.yaml`). JSON Schema is the validation standard; YAML is the authoring format. The same schema validates schedule data files in the editor (Red Hat YAML + `yaml.schemas`) and in library code.

## Adding library code

New code must be modular and composable:

- One capability per module (parse predecessors, validate, CPM forward pass, calendar, render)
- Modules callable independently
- Unit-testable in isolation
- Thin scripts compose modules; the agent may also compose them step by step

Full specification: `references/prd.md`.

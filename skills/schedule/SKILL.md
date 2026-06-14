---
name: schedule
description: Text-native Microsoft Project Auto Schedule alternative using YAML schedule files and deterministic CPM calculation. Use whenever the user mentions project schedules, Gantt charts, task dependencies, predecessors, milestones, critical path, MS Project-style planning, landscaping/construction/renovation timelines, or wants to create, edit, or visualize a schedule without a traditional PM app — even if they do not say "schedule file" or name this skill.
---

# Schedule

If this skill is invoked, apply every standard below in full.

A text-native alternative to Microsoft Project Auto Schedule. The schedule lives in YAML files the user and agent edit. **Library code calculates dates (CPM); the agent never does date math.**

`README.md` holds the human-facing guide (how to run the tool, the compute→refresh loop, viewing the Gantt). Read it when the user asks you to do something operational on their behalf — running commands, explaining how to view or refresh the chart, or setting up editor validation.

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
  site/            # generated viewer — never edit; safe to delete
    gantt_data.json
    gantt.html
    gantt.js
    gantt_theme.css
```

`compute` writes Gantt artifacts into **`site/`** under the project directory. They are **generated — never edit; safe to delete**; edit `schedule.yaml` instead.

The schedule filename is not fixed. Ask the user for the **schedule file path** or **project directory** if not provided.

## Workflow

### 1. Locate the project

If the user gives a directory, find the schedule YAML (ask if multiple). If they give a file path, use its parent as the project directory.

Read `context/glossary.md` before editing — it defines domain terms. Read `context/data_model.md` when creating or structurally changing items. Read `context/architecture.md` for how validation and compute fit together.

### 2. Edit the schedule (agent)

Edit YAML directly. Rules that matter most:

**Three kinds** — `kind` is always the **first field** on every item:

| Kind | Key fields | Forbidden |
|------|------------|-----------|
| `milestone` | `date` (user-set, must be a working day) | `duration`, `timing`, `predecessors`, `children` |
| `task` | `timing`, `duration`, `predecessors` (plus `start`/`finish` when timing requires) | `date`, `children` |
| `group` | `predecessors`, `children` (min 1) | `date`, `duration`, `timing` |

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

**Task timing:** every task requires `timing: auto | start_duration | start_finish | finish_duration`. Use `auto` for planning (duration + predecessors → computed dates). Use pinned modes during execution when a start or finish is committed — see `context/data_model.md`. Pinned `start`/`finish` values are authoritative; predecessors and the parent group define earliest allowable bounds. A pin earlier than those bounds is a **hard validation error** (`validate_pinned_task_bounds`) — adjust the pin, predecessors, or milestone gates, never the tool.

**Milestone reachability:** a milestone `date` that its own predecessor chain cannot finish by is a **hard error** (`validate_milestone_reachability`). Fix by moving the milestone date later, shortening upstream durations, or relaxing predecessors.

**Calendar file** — `weekends` and `holidays` are both required (`holidays` may be empty):

```yaml
weekends: [sat, sun]      # any of mon..sun; non-working days
holidays:                 # ISO dates excluded from working days
  - 2026-07-04
```

Durations and lag count working days only. Milestone dates must fall on a working day.

**Task order:** controlled by user and agent — scheduling code never rewrites it. The `items` list is also the **Gantt row order** (top-to-bottom timeline), so order items as a coherent date sequence, not grouped by kind: each parent group directly above its children, top-level siblings by computed start date, and milestones inline where they fall (not stacked at the top). After changing predecessors or durations, recompute and reorder rows if unrelated work would otherwise be separated vertically.

**Milestones** are the only user-defined date constraints. Their `date` is authoritative and must fall on a working day in the calendar file.

### 3. Run the toolchain (library)

From `skills/schedule/` (run `uv sync` once):

```bash
uv run validate <schedule-file>   # validate only (JSON Schema + logic rules)
uv run compute <schedule-file>    # validate, compute CPM, render Gantt, serve
```

`compute` validates, runs CPM, deploys the Gantt viewer into `site/`, and serves it (add `--no-serve` for CI). Full flags and the view/refresh loop are in `README.md`.

When validation fails, read **all** error messages — each is specific (duplicate id, unknown predecessor, non-working-day milestone, cycle, listing-rule, pinned-bound, unreachable milestone). Fix the **schedule or calendar YAML** they point to; never patch the library to bypass a rule.

**Before editing YAML to fix errors**, present to the user (unless they already asked you to fix it):

1. **Every error** — quote each message from the tool output.
2. **Your planned fix for each** — what changes in the YAML and why.

Then edit, re-run `validate`, and repeat until clean. The library never writes fixes — that is always the agent's job.

### 4. Report results (agent)

The Gantt viewer is the user's source of truth for computed dates and critical path — point them to it (the URLs `compute` prints) rather than transcribing the JSON. Summarize only what's useful in chat (e.g. project finish, a notable conflict).

Never fix a validation problem by writing computed `start`/`finish` onto tasks or groups — only milestones have user-set dates, via `date`.

## Editor hints

When you create or edit a user project, add a schema modeline as the **first line** of both files (so Red Hat YAML validates inline), unless the user opts out:

```yaml
# yaml-language-server: $schema=./schemas/schedule.schema.yaml
```

```yaml
# yaml-language-server: $schema=./schemas/calendar.schema.yaml
```

Adjust the relative path to where the schemas live. Setup detail for the user is in `README.md`.

## When NOT to use

- User wants interactive Gantt drag-and-drop editing
- User wants resource leveling, cost tracking, or cross-project links

## References

- `README.md` — human-facing guide (running the tool, viewing/refreshing the Gantt, editor setup)
- `context/data_model.md` — field rules, predecessor and timing examples (read when authoring or restructuring items)
- `context/glossary.md` — domain glossary (read before editing)
- `schemas/schedule.schema.yaml`, `schemas/calendar.schema.yaml` — the validation contract, JSON Schema authored in YAML; same schemas run at validate time and (via Red Hat YAML) in the editor
- `context/prd.md`, `context/architecture.md`, `context/scheduling_algorithm.md` — deeper background on requirements, design, and the CPM algorithm

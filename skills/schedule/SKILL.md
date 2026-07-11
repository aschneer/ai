---
name: schedule
description: Only use when explicitly invoked as /schedule. Text-native Microsoft Project Auto Schedule alternative using YAML schedule files and deterministic CPM calculation.
disable-model-invocation: true
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
  .gitignore       # written by compute if absent — ignores site/; never overwritten
  site/            # generated viewer — never edit; safe to delete
    gantt_data.json
    gantt.html
    gantt.js
    gantt_theme.css
```

`compute` writes Gantt artifacts into **`site/`** under the project directory. They are **generated — never edit; safe to delete**; edit `schedule.yaml` instead. It also drops a `.gitignore` (ignoring `site/`) into the project directory when one is absent — an existing `.gitignore` is never overwritten.

The schedule filename is not fixed. Ask the user for the **schedule file path** or **project directory** if not provided.

## Workflow

### 1. Locate the project

If the user gives a directory, find the schedule YAML (ask if multiple). If they give a file path, use its parent as the project directory.

Read `context/glossary.md` before editing — it defines domain terms. Read `context/data_model.md` when creating or structurally changing items. Read `context/architecture.md` for how validation and compute fit together.

### 2. Edit the schedule (agent)

Edit YAML directly. Rules that matter most:

**File section order** — keep top-level keys in this order: `calendar`, then `people` and `events` (if present), then `items`. Both context bands must be authored **above** `items`; they render as bands at the top of the Gantt (people first, then events).

**People and events (optional)** — two decorative context bands, same shape, drawn above the schedule. Pure annotation: no IDs, no predecessors, never affects scheduling, the critical path, or project finish. Each entry has a `name` and `segments`; each segment is `{start, finish, label}` (all required). Segments use **any calendar day** (weekends allowed), `finish` is inclusive, and segments within one band **must not overlap** (hard error).
- **`people`** — one row per person: "out of office", "on vacation", "traveling", work location.
- **`events`** — calendar context not tied to a person: company events, holidays of note, external dates.

```yaml
people:
- name: Maria
  segments:
  - {start: 2026-05-11, finish: 2026-05-15, label: Out of office}
  - {start: 2026-06-15, finish: 2026-06-26, label: On vacation}
events:
- name: Company
  segments:
  - {start: 2026-07-04, finish: 2026-07-04, label: Independence Day}
```

**Three kinds** — `kind` is always the **first field** on every item:

| Kind | Key fields | Forbidden |
|------|------------|-----------|
| `milestone` | `date` (user-set, must be a working day); optional deadline `predecessors` and `type: project_finish` | `duration`, `timing`, `children` |
| `task` | `timing`, `duration`, `predecessors` (required for `auto`; optional for pinned modes; plus `start`/`finish` when timing requires) | `date`, `children` |
| `group` | `children` (min 1); `predecessors` optional | `date`, `duration`, `timing` |

**ID 0** is reserved for the project start milestone. IDs are stable and **must be unique** — never renumber when reordering items.

**Predecessors** — inline list of MS Project strings only:

```yaml
predecessors: ["0FS"]
predecessors: ["5FS", "7SS+2d"]
predecessors: ["10SS"]
```

Predecessors are **required only for `auto` tasks** (duration alone gives no dates). Pinned tasks (`start_duration`, `start_finish`, `finish_duration`) and groups may **omit** `predecessors` — a pinned task sets its own dates, a group rolls up from children. An item with no predecessors draws **no dependency arrow**; use this for items that just occupy calendar space (e.g. team availability). A self-anchoring item may still list real predecessors when it has them.

Listing rules (when an item **has** predecessors):
- Only **immediate** predecessors — not the full transitive chain
- Top-level item with no other preds → `["0FS"]` only
- Child with no other preds → `["{parentId}SS"]` only
- Otherwise list specific preds — **never** mix in `0FS`
- Self-anchoring item with no dependency → omit `predecessors` (do not write a placeholder `0FS`/`{parentId}SS`)
- Milestone predecessors are a deadline annotation only — **FS, no lag** (`["42FS"]`), never `0FS`, never self-referential (see below)
- No cyclic predecessor dependencies

**Durations and lag:** days and weeks only (`4d`, `2w`). No hours.

**FS start day** — with zero lag, an FS successor of a **task or group** starts the **next working day** after the predecessor finishes (the predecessor occupies its finish day). An FS successor of a **milestone** — including `0FS` from project start — starts **on** the milestone date itself (a milestone is an instantaneous point). To push a milestone's successor to the next day, add lag: `13FS+1d`. This matches Microsoft Project; detail in `context/data_model.md`.

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

**Milestone deadlines (predecessors)** — a milestone may list a predecessor to mark that a chain of work **culminates in that fixed date** (a deadline). The predecessor is **annotation only**: the milestone's `date` always prevails, the link never moves it. Rules: **finish-to-start, no lag** (`predecessors: ["42FS"]` where 42 is the last task of the chain); never `0FS`; never self-referential. It draws the dependency arrow into the milestone. If the feeding chain finishes **after** the date, the deadline is unreachable — a hard error (`validate_milestone_reachability`).

**Project-finish milestone (`type: project_finish`)** — designate **at most one** milestone as the project finish by adding `type: project_finish`. It **must** list a deadline predecessor chain (the culminating work). Its `date` is the project deadline; the reported **project finish** is when that chain **actually completes**, which may be *earlier* than the date (buffer) — matching Microsoft Project (finish = work end; deadline shown separately). The **critical path** is the zero-slack chain feeding it (empty when there is buffer). With no designated milestone, project finish is the latest computed finish and the critical path is the longest path to it. A plain deadline milestone (no `type`) never marks its chain critical — only the designated one does. Full rules and examples: `context/data_model.md`.

```yaml
- kind: milestone
  id: 50
  name: Launch
  date: 2026-06-19
  type: project_finish
  predecessors: ["42FS"]
```

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
- `context/task_timing_modes.md` — pinned-date timing modes in depth (`start_duration`, `start_finish`, `finish_duration`)
- `context/glossary.md` — domain glossary (read before editing)
- `schemas/schedule.schema.yaml`, `schemas/calendar.schema.yaml` — the validation contract, JSON Schema authored in YAML; same schemas run at validate time and (via Red Hat YAML) in the editor
- `context/prd.md`, `context/architecture.md`, `context/scheduling_algorithm.md` — deeper background on requirements, design, and the CPM algorithm

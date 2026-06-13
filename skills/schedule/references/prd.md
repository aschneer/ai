# Project Schedule — Product Requirements Document

**Status:** Draft (in design)
**Last updated:** 2026-06-07

## Overview

An **AI agent skill** that provides a text-native alternative to Microsoft Project Professional Auto Schedule. The schedule lives in human-readable YAML files that a user and an AI agent edit. Deterministic library code performs schedule calculation (critical-path method); the agent handles editing, orchestration, and interpretation. A script generates a static HTML Gantt chart from computed output.

## Design principles

1. **File is source of truth** — not a UI, not chat history
2. **Agent-native editing** — the skill teaches the agent to read and write schedule files; the agent does not perform date math
3. **Deterministic scheduling** — all date calculation is library code, never LLM inference
4. **Minimal code** — before writing code for any capability, ask whether the skill can instruct the agent to do it instead; prefer code only where correctness requires it
5. **Modular libraries** — code lives in small, independently callable libraries composed by scripts or the agent
6. **Read-only engine** — scheduling code validates and computes; it never modifies schedule or calendar files
7. **Microsoft Project semantics** — Auto Schedule, rollup scheduling, predecessor syntax, and duration notation

## Architecture

### Deliverable

This project produces an **AI agent skill** (`SKILL.md` + supporting libraries and schemas), not a standalone application.

### Agent vs deterministic code

| Responsibility | Who |
|----------------|-----|
| Edit schedule/calendar YAML | Agent (guided by skill) |
| Ask user for schedule path | Agent |
| Validate files against schema | Library |
| Schedule calculation (CPM) | Library |
| Calendar / working-day math | Library |
| Generate HTML Gantt | Library (or thin script composing libraries) |
| Interpret warnings, suggest fixes | Agent |
| Decide task order in schedule file | User and agent |

An agent *could* read a schedule file and produce HTML directly, but that risks arithmetic and dependency errors. **Schedule calculation must always be deterministic code.**

Before implementing any new capability, evaluate: *can the skill instruct the agent to do this?* Write library code only when the answer is no — typically validation, graph algorithms, calendar math, and rendering.

### Library structure

All code must be organized as **composable libraries**:

- Each distinct capability lives in its own module (e.g. parse predecessors, validate schema, forward-pass scheduling, calendar lookup, render Gantt)
- Modules are callable independently — no monolithic pipeline required
- Thin orchestration scripts (or the agent) compose modules on demand
- Modules must be unit-testable in isolation

### Project directory

A schedule project lives in a **single directory** containing everything for that schedule:

```
my-renovation/
  schedule.yaml       # any filename; user or agent chooses
  calendar.yaml       # referenced by path from schedule file
  gantt.html          # generated output (optional)
```

- The schedule filename is **not prescribed** — the skill asks the user for the schedule file path (or project directory)
- The `calendar` field in the schedule file uses a path **relative to the schedule file's location**
- All schedule-related artifacts stay co-located in one folder

---

## Data model

Every item in the schedule is one of three **kinds**. The `kind` field is the **primary discriminator** — it is listed first on every item and determines which other fields are legal. All validation is driven by `kind`; no field may appear on a kind that forbids it.

### Kind comparison

| | **Milestone** | **Task** | **Group** |
|--|---------------|----------|----------------------|
| **Purpose** | Pin a fixed date in the schedule | Work that takes time | Group children into a roll-up container |
| **Duration** | Zero (implicit) | User-entered (`4d`, etc.) | Derived from children's span |
| **`date` in file** | User-set, authoritative | None — computed at render | None — computed at render |
| **Predecessors** | Cannot have any | Required inline list | Required inline list |
| **Children** | Cannot have any | Cannot have any | Required (minimum 1, strict) |
| **MS Project parallel** | Milestone | Regular task | Summary task |

### Field constraints by kind

| Field | **Milestone** | **Task** | **Group** |
|-------|---------------|----------|-------------|
| `kind` | `milestone` | `task` | `group` |
| `id` | required | required | required |
| `name` | required | required | required |
| `date` | required (user-set) | **forbidden** | **forbidden** |
| `duration` | **forbidden** (implicit 0) | required | **forbidden** (derived) |
| `predecessors` | **forbidden** | required | required |
| `children` | **forbidden** | **forbidden** | required (**min 1**, strict) |

### Item field order

`kind` is always the **first field** on every item, followed by `id`, then remaining fields for that kind. This makes the discriminator visible before any other data.

```yaml
- kind: task
  id: 11
  name: Trim the hedges
  duration: 2d
  predecessors: ["10SS"]
```

### Schema validation

The project ships **JSON Schema** files **authored in YAML** (e.g. `schemas/schedule.schema.yaml`, `schemas/calendar.schema.yaml`). JSON Schema is the validation standard — it defines structure, types, and constraints. YAML is the authoring format for both the schemas and the schedule data files.

The `kind` field selects a sub-schema via `oneOf`; all other fields are validated against that sub-schema only.

- The scheduling engine validates **before** calculating — invalid files are rejected with clear errors
- Editor YAML extensions use the same schema files for live squiggles (Red Hat YAML + `yaml.schemas`, or a modeline: `# yaml-language-server: $schema=./schemas/schedule.schema.yaml`)
- A group with zero children is **invalid at schema level** (`children.minItems: 1`) — not merely a runtime warning

### Group kind naming

Microsoft Project calls this a **summary task**. We use **`group`** instead — shorter, avoids confusion with report/summary language, and reads naturally in YAML (`kind: group`). Other names considered and rejected: `category`, `phase`, `section`, `container`, `rollup`, `block`, `package`, `summary`.

### Examples

**Valid:**

```yaml
calendar: calendar.yaml
items:
  - kind: milestone
    id: 0
    name: Project start
    date: 2026-06-09

  - kind: group
    id: 10
    name: Update the landscaping
    predecessors: ["3FS"]
    children:
      - kind: task
        id: 11
        name: Trim the hedges
        duration: 2d
        predecessors: ["10SS"]

      - kind: milestone
        id: 13
        name: Permit approved
        date: 2026-06-20

      - kind: task
        id: 14
        name: Re-landscape beds
        duration: 3d
        predecessors: ["13FS"]

  - kind: task
    id: 20
    name: Install pavers
    duration: 4d
    predecessors: ["0FS"]
```

**Invalid (rejected by schema):**

```yaml
items:
  # INVALID: milestone cannot have predecessors, duration, or children
  - kind: milestone
    id: 99
    name: Bad milestone
    date: 2026-06-15
    duration: 0d
    predecessors: ["12FS"]

  # INVALID: task cannot have date or children
  - kind: task
    id: 100
    name: Bad task
    duration: 2d
    date: 2026-06-15
    predecessors: ["0FS"]

  # INVALID: group must have at least one child
  - kind: group
    id: 101
    name: Empty group
    predecessors: ["0FS"]
    children: []
```

---

## Requirements

### R0 — Project start milestone (ID 0)

Every schedule must begin with a **project start** task:

- **Unique ID:** `0` (reserved; never reassigned)
- **`kind`:** `milestone`
- **Role:** anchors the entire project — every other task is ultimately constrained to start after this milestone
- **`date`:** the project start date, set by the user

Task 0 is a **milestone** (R11) — the special case that anchors the entire project. It is the global scheduling anchor, analogous to how a parent task anchors its children (see R2, R5).

### R1 — Task list

The system must track a list of schedule items. Every item has at minimum:

- A stable integer **Unique ID** (not list position; never renumbered)
- A **`kind`** discriminator as the **first field** (see Data model) — `milestone`, `task`, or `group`
- A **name** (human-readable label)

Additional fields depend on `kind` (see **Data model**).

### R2 — Multi-level task hierarchy

The system must support groupings of tasks at multiple levels:

- A parent item (group kind) can contain child items
- Children can themselves be parents (arbitrary nesting depth)
- Hierarchy is visible in the schedule file (indented YAML)

**Example:** "Update the landscaping" contains "Trim the hedges", "Trim the lawn", "Re-landscape the flower beds".

**Parent task predecessors:** A parent task **may** have its own predecessor links. When it does:

- The parent's effective start is constrained by its predecessors (like any other task)
- **No child task within that parent may start before the parent's start date**
- The parent acts as a **local project start** (a local ID 0) for its subtree — children inherit the parent's start as their earliest allowable start, then apply their own predecessors and durations within that bound

### R3 — Group duration rollup

For any **group** item, duration and dates must be **derived**, not entered:

- **Duration** = span from earliest child start to latest child finish (not a sum of child durations)
- **Start** = earliest child start date (but not earlier than the parent's own predecessor constraints — see R2)
- **Finish** = latest child finish date

Groups may also have predecessors (R2), which can push the group's start (and therefore all children) later.

### R4 — Task duration entry

The user must be able to enter a duration for each **leaf** task (a task with no children). Duration is the expected **working time** to complete the task, expressed in Microsoft Project style notation (see R12).

Groups and milestones do not have user-entered durations — they are computed (group) or fixed at zero (milestone).

### R5 — Predecessor relationships

The user must be able to define predecessor relationships between tasks using **Microsoft Project link semantics**.

**Storage format (schedule file):** On items that support predecessors (`task` and group kinds), `predecessors` is **always an inline YAML list** of MS Project format strings:

```yaml
predecessors: ["5FS", "7SS+2d"]
predecessors: ["0FS"]
predecessors: ["10SS"]
```

Block-style bulleted lists must not be used — inline lists keep the file concise.

| Component | Format | Default |
|-----------|--------|---------|
| Task reference | Integer Unique ID | — |
| Link type | `FS`, `SS`, `FF`, `SF` | `FS` |
| Lag / lead | `+3d` (lag), `-2d` (lead) | zero |

**Examples:**

- `"5"` or `"5FS"` — task 5, finish-to-start, no lag
- `"14FS+3d"` — task 14, finish-to-start, 3-day lag
- `"7SS+2d"` — task 7, start-to-start, 2-day lag
**Predecessor listing rules:**

Each task lists only its **immediate** predecessors — the tasks that directly prevent it from starting. Do not list transitive predecessors.

| Situation | Required predecessors |
|-----------|----------------------|
| Top-level task, no other predecessors | `["0FS"]` — task 0 only |
| Child task, no other predecessors | `["{parentId}SS"]` — parent only, start-to-start (see R2) |
| Task with specific predecessors | Those predecessors only — **never** include `0FS` |

A task's predecessor list must be **either** `["0FS"]` alone **or** one or more other predecessor links with no `0FS` mixed in.

**Link types (Microsoft Project standard):**

| Type | Meaning |
|------|---------|
| FS | Successor cannot start until predecessor finishes |
| SS | Successor cannot start until predecessor starts |
| FF | Successor cannot finish until predecessor finishes |
| SF | Successor cannot finish until predecessor starts |

The scheduling engine parses these strings (same grammar as Microsoft Project).

**Milestone predecessor equivalence (R11):** Because a milestone has zero duration, its start and finish are the same date. When a predecessor link references a milestone, all link types are equivalent — `13FS`, `13SS`, `13FF`, and `13SF` all resolve to that single date.

### R6 — Stable Unique IDs

Task identifiers must behave like Microsoft Project **Unique ID**:

- **ID 0** is reserved for the project start milestone (R0)
- IDs 1+ assigned once when a task is created (next available integer)
- **Never automatically renumbered** when tasks are reordered in the file
- Predecessor references remain valid after reordering
- Gaps in the ID sequence are acceptable after task deletion
- **Do not** imply list position — integers are opaque references, not ordinals. File order and editor line numbers convey position.

### R7 — Auto Schedule

The system must automatically calculate start and finish dates for all tasks based on:

- Task durations (days and weeks; see R12)
- Predecessor relationships (including link type and lag/lead)
- Project start milestone (task 0)
- Parent predecessor constraints on children (R2)
- Working calendar — weekends and holidays excluded (R13)

The user must **not** need to manually set start/finish dates on leaf tasks in Auto Schedule mode.

Group dates roll up from children (R3). Project finish date = latest finish among all items.

### R8 — Human-readable agent-editable data store

Schedule data must be stored in simple, human-readable structured files (indented YAML) that:

- Both a user and an AI agent can read and edit directly
- Support version control (git diffs)
- Show task hierarchy clearly (indentation + optional editor fold/collapse)
- **Task order** is controlled by the user and agent — not rewritten by tooling (see **Task order** in context.md for recommended convention)

Non-milestone items have **no date fields** in the schedule file (R14). Computed dates appear only in engine output (Gantt, reports).

### R9 — Gantt chart rendering

The schedule must be renderable as a Gantt chart view.

- **`compute`** writes **`gantt_data.json`** (computed dates and metadata) and deploys static **`gantt.html`** + **`gantt.js`** into the project directory
- The viewer loads JSON over HTTP (not `file://`); a dev server is started by default (see R24)
- Output includes **`is_critical`** on each item for critical-path highlighting
- Output includes parsed **`predecessors`** on each item for dependency link rendering in the viewer
- The viewer draws task/group bars, milestones, predecessor links (FS/SS/FF/SF anchors), and distinct styling for critical items
- Live editing of the Gantt is **not** required
- Regenerated on demand when the user or agent runs **`compute`**

### R10 — Hot reload (nice to have)

If the Gantt is a web-page-based artifact, it should hot-reload when the underlying schedule file changes during development.

### R24 — Gantt dev server

After **`compute`**, the skill may start a lightweight HTTP server so the user can open the Gantt in a browser.

- Default bind: **`0.0.0.0`** (`--host auto`) so the chart is reachable on the network (LAN, Tailscale, etc.)
- Print **local** (`127.0.0.1`) and **network** URLs; the user clicks or copies a URL into their browser — no auto-open
- Over SSH, the local URL works when the environment forwards the port (Cursor/VS Code, or `ssh -L`)
- Optional **`SCHEDULE_VIEWER_HOST`** env var overrides the network hostname in printed URLs
- **`--host 127.0.0.1`** for loopback-only; **`--no-serve`** when files only (CI)
- No Node/Vite toolchain — Python static server only (see `references/decisions.md`)

### R25 — Critical path

After CPM, the engine must identify items on the chain that drives **project finish** and set **`is_critical: true`** on those items in JSON output (others `false`). The Gantt viewer uses this for bar styling. The agent reports critical items from the same field.

### R11 — Milestones

The system must support **milestones** (`kind: milestone`):

- A milestone has **zero duration** (implicit — no `duration` field) and a user-entered **`date`**
- A milestone has a stable **Unique ID**
- A milestone **cannot have predecessors** — it can only *be* a predecessor of other tasks
- The user-set **`date` is authoritative** — the scheduling engine does not override it
- **Milestones are the only mechanism** for applying a user-defined date constraint at a specific point in the schedule; other tasks reference that point via predecessor links
- The project start (ID 0) is a milestone — the special case that anchors the entire project (R0)

**Milestone predecessor equivalence:** When any predecessor link targets a milestone, link type does not matter — FS, SS, FF, and SF all resolve to the milestone's single `date`.

### R14 — No date fields on non-milestone items

In the schedule file, **only milestones** (`kind: milestone`) have a `date` field. All other timing is computed at render time (Gantt, reports), not stored in the source file.

### R15 — Schema validation

Schedule files must conform to the **Data model** defined above. See JSON Schema requirements under Schema validation in the Data model section.

### R16 — Read-only scheduling engine

The scheduling engine and all library code must **never modify** schedule or calendar files. On run:

- **Validate** files against JSON Schema (`.schema.yaml` files) — reject with clear errors if invalid
- **Compute** dates and produce output (stdout, JSON, HTML Gantt, etc.)
- **Warn** on schedule logic problems (e.g. impossible predecessor chains, tasks that cannot meet a milestone date) — but do not write back to source files

Only the user and agent edit schedule data.

### R17 — Project directory

Each schedule project must live in a dedicated directory containing the schedule file, calendar file, and generated artifacts (Gantt HTML, etc.). The skill asks the user for the schedule file path or project directory. Schedule filename is not prescribed.

### R18 — Schedule inconsistency warnings

Because milestones cannot have predecessors (R11), there is no "milestone date vs predecessor" conflict on the milestone itself. The engine may still **warn** when the computed schedule for *other items* cannot satisfy a milestone date — for example, a task chain implies work finishes after a milestone it must reach. These are schedule logic warnings, not file edits.

### R12 — Duration notation

Durations and lag/lead values use **Microsoft Project style** suffix notation. MVP supports **days and weeks only**:

| Suffix | Meaning |
|--------|---------|
| `d` | working days |
| `w` | weeks (converted to working days via calendar) |

**Examples:** `4d`, `2w`, `3d` lag in `5FS+3d`, `1w` lag in `7SS+1w`

All duration arithmetic respects the working calendar (R13) — a duration of `4d` means four working days, skipping weekends and holidays.

### R13 — Working calendar

The system must map the schedule onto a **real calendar**:

- **Weekends:** no work occurs on Saturday or Sunday (MVP)
- **Holidays:** no work occurs on configured holidays (MVP)
- Schedule dates are **calendar dates**; durations are **working-day durations**
- Start/finish calculations skip non-working days when counting duration and applying lag/lead

**Calendar file:** Holidays and calendar configuration live in a **separate file** in the same project directory as the schedule. The schedule file references it by path relative to the schedule file's location.

```yaml
# schedule file (any filename)
calendar: calendar.yaml
items:
  - kind: milestone
    ...
```

```yaml
# calendar.yaml
weekends: [sat, sun]
holidays:
  - 2026-07-04
  - 2026-12-25
```

The scheduling engine loads both files and validates each against its schema before calculating.

---

## Out of scope (MVP)

- Interactive Gantt editing (drag bars, drag links)
- Hour-based durations and lag (`8h`) — days and weeks only
- Engine rewriting schedule file order or content
- Cross-project predecessor links (`C:\other.mpp\3FF`)
- Resource assignment / leveling
- Cost tracking
- Partial work days / custom work weeks (e.g. 4-day week)
- Baselines / actuals / % complete

---

## Implement later

Features designed but not yet built. Full design: `task_timing_modes.md`.

### R19 — Task timing mode (required field)

Every **`kind: task`** item must include a **`timing`** field — never optional, never inferred. Allowed values:

| `timing` | User specifies | Engine computes |
|----------|----------------|-----------------|
| `auto` | `duration`, `predecessors` | `start`, `finish` |
| `start_duration` | `start`, `duration`, `predecessors` | `finish` |
| `start_finish` | `start`, `finish`, `predecessors` | `duration` |
| `finish_duration` | `finish`, `duration`, `predecessors` | `start` |

Existing schedules must be updated to include `timing: auto` on every task — no backward compatibility for omitted `timing`.

### R20 — Task date fields by timing mode

- **`auto`:** `start` and `finish` forbidden in the schedule file; computed only.
- **`start_duration`:** `start` required; `finish` forbidden.
- **`start_finish`:** `start` and `finish` required; `duration` forbidden.
- **`finish_duration`:** `finish` required; `start` forbidden.

Milestones keep a single authoritative **`date`** field. Groups have no user-entered dates (R3 unchanged).

### R21 — Predecessors on pinned tasks

`predecessors` remain **required** on all tasks in all timing modes. Fixed `start` / `finish` values are authoritative. Predecessors define earliest allowable bounds — not computed dates for pinned fields.

### R22 — Pinned-task validation (fail fast)

When validation detects an impossible schedule, reject with a hard error before compute:

- Pinned `start` before predecessor-implied earliest start → error
- Pinned `finish` before predecessor-implied earliest finish → error
- `start_finish` with `start` after `finish`, or zero working-day span → error
- Pinned child `start` before parent group floor → error

No warnings channel and no automatic adjustment of user pins.

### R23 — Pinned-task compute

The scheduling engine derives the third field (start, finish, or duration) from the two user-specified fields using working-calendar math. Pinned fields are not overwritten during the fixed-point iteration. `auto` tasks use the existing CPM forward pass unchanged.

**Out of scope for R19–R23:** fixed dates on groups (use milestone + predecessor on the group); hour durations; YAML layout changes.

---

## Open questions

- [x] File format for predecessors: list of MS Project format strings (uniform schema)
- [x] Identifier type: stable integer Unique ID; ID 0 reserved for project start
- [x] Duration units: days and weeks only (`4d`, `2w`); hours out of scope
- [x] Calendar: weekends and holidays excluded for MVP
- [x] Predecessors on group items: allowed; constrains earliest child start
- [x] Group children: min 1 child, enforced strictly at schema level
- [x] `kind` is first field; primary discriminator for all validation
- [x] Group kind name: `group`
- [x] Predecessor listing: immediate predecessors only; `0FS` alone OR other preds without `0FS`; child with no preds lists parent as `SS`
- [x] Child→parent predecessor link: `{parentId}SS` (start-to-start)
- [x] Predecessor format: inline YAML lists only
- [x] Milestones: user-entered authoritative `date`; no predecessors; only date constraint mechanism
- [x] Task kinds: `milestone` / `task` / `group` discriminator with JSON Schema validation
- [x] Holiday list: separate calendar file in project directory, path relative to schedule file
- [x] Task timing modes: designed — see Implement later (R19–R23) and `task_timing_modes.md`
- [x] Gantt output: JSON + static HTML/JS viewer via `compute`
- [x] Gantt dev server: local + network URLs, no auto-open (R24)
- [x] Critical path: `is_critical` per item (R25)
- [x] Schedule filename: arbitrary; skill asks user for path
- [x] Engine: read-only — validate, compute, warn; never edit schedule files
- [x] Deliverable: skill with modular composable libraries

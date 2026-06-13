# Project Schedule — Product Requirements Document

**Status:** Active  
**Last updated:** 2026-06-07

## Purpose

A text-native alternative to Microsoft Project **Auto Schedule**. The schedule lives in human-readable YAML that a user and an AI agent edit. A deterministic engine calculates dates; the agent handles editing and interpretation. The user views results in a Gantt chart and reports.

## Deliverable

An **AI agent skill** (`SKILL.md` + validation schemas + scheduling libraries), not a standalone application.

## Who it's for

- Users managing renovation, landscaping, construction, or similar projects
- Users who want schedules in **git**, editable in an editor or by an agent
- Users who need **Auto Schedule** behavior: durations + dependencies → computed dates

## Product principles

1. **The schedule file is the source of truth** — not chat history, not a proprietary database
2. **Agent-assisted editing** — the agent reads and writes schedule files; it does **not** perform date math
3. **Deterministic scheduling** — all date calculation is library code, never LLM inference
4. **Microsoft Project semantics** — Auto Schedule, rollup scheduling, predecessor syntax, duration notation
5. **Human-readable projects** — one folder per schedule, version-control friendly
6. **Read-only engine** — scheduling code validates and computes; it never modifies schedule or calendar files

Engineering choices (modules, CLIs, algorithms): `architecture.md`. Examples and editing cheat sheet: `data_model.md`.

---

## Agent vs deterministic code

| Responsibility | Who |
|----------------|-----|
| Edit schedule/calendar YAML | Agent (guided by skill) |
| Ask user for schedule path | Agent |
| Validate files against schema | Library |
| Schedule calculation (CPM) | Library |
| Calendar / working-day math | Library |
| Generate Gantt (JSON + viewer) | Library |
| Report validation errors, suggest fixes | Agent |
| Task order in schedule file | User and agent |

An agent *could* read a schedule file and compute dates or produce a Gantt directly, but that risks arithmetic and dependency errors. **Schedule calculation must always be deterministic library code** — never LLM inference.

When validation fails, the agent fixes the **schedule file** — never patches skill code to bypass a rule. List every error and planned YAML fix before editing (unless the user already asked for fixes).

---

## Schedule file format

These are **hard requirements** on what users and agents write. The skill ships schemas that enforce this structure; invalid files are rejected (R15).

### Header

```yaml
calendar: calendar.yaml   # optional; path relative to this schedule file
items:
  - kind: milestone
    ...
```

Schedule items live under **`items`**. The schedule filename is not prescribed.

### Three kinds

Every item is **`milestone`**, **`task`**, or **`group`**. The **`kind`** field is the primary discriminator — it is **always the first field** on every item and determines which other fields are legal. No field may appear on a kind that forbids it.

| | **Milestone** | **Task** | **Group** |
|--|---------------|----------|----------------------|
| **Purpose** | Pin a fixed date | Work that takes time | Roll-up container for children |
| **Duration** | Zero (implicit) | User-entered (`4d`, etc.) | Derived from children's span |
| **`date` in file** | User-set, authoritative | Forbidden — computed | Forbidden — computed |
| **Predecessors** | Forbidden | Required inline list | Required inline list |
| **Children** | Forbidden | Forbidden | Required (minimum 1, strict) |
| **MS Project parallel** | Milestone | Regular task | Summary task |

We use **`group`**, not `summary` or `phase` — see `decisions.md` (Resolved product decisions).

### Field constraints by kind

| Field | Milestone | Task | Group |
|-------|-----------|------|-------|
| `kind` | `milestone` | `task` | `group` |
| `id` | required | required | required |
| `name` | required | required | required |
| `date` | required (user-set) | **forbidden** | **forbidden** |
| `timing` | **forbidden** | required | **forbidden** |
| `duration` | **forbidden** | conditional | **forbidden** |
| `start` / `finish` | **forbidden** | conditional | **forbidden** |
| `predecessors` | **forbidden** | required | required |
| `children` | **forbidden** | **forbidden** | required (**min 1**) |

### Item field order

`kind` first, then `id`, then remaining fields for that kind:

```yaml
- kind: task
  id: 11
  name: Trim the hedges
  duration: 2d
  predecessors: ["10SS"]
```

### Validation

- Schedule and calendar files must conform to this format. The skill ships **JSON Schema** files authored in YAML (`schemas/schedule.schema.yaml`, `schemas/calendar.schema.yaml`).
- The same schemas power **editor validation** via Red Hat YAML and a modeline on each file (`# yaml-language-server: $schema=…` on schedule and calendar). Workspace `yaml.schemas` is optional; see `SKILL.md` **Editor hints**.
- **`kind`** selects a sub-schema; forbidden fields on a kind are **schema errors**, not runtime surprises.
- A group with zero children is invalid at schema level.

More examples: `data_model.md`.

---

## Calendar file format

Holidays and weekend configuration live in a **separate YAML file** in the project directory. The schedule references it by relative path (R13).

```yaml
weekends: [sat, sun]
holidays:
  - 2026-07-04
  - 2026-12-25
```

---

## Requirements

### R0 — Project start milestone (ID 0)

Every schedule must begin with a **project start** item:

- **Unique ID:** `0` (reserved; never reassigned)
- **`kind`:** `milestone`
- **`date`:** the project start date, set by the user
- **Role:** anchors the entire project — all other work is ultimately constrained from this date

Task 0 is the global scheduling anchor, analogous to how a parent group anchors its children (R2, R5).

### R1 — Task list

The system tracks a list of schedule items. Every item has:

- A stable integer **Unique ID** (not list position; never renumbered)
- A **`kind`** discriminator as the **first field** (see Schedule file format)
- A **name** (human-readable label)

Additional fields depend on `kind`.

### R2 — Multi-level hierarchy

- A **group** can contain child items at arbitrary nesting depth
- Hierarchy is visible in the schedule file (indented YAML)

**Parent group predecessors:** A group **may** have predecessor links. When it does:

- The group's effective start is constrained by its predecessors
- **No child within that group may start before the group's start date**
- The group acts as a **local project start** for its subtree

### R3 — Group duration rollup

For any **group**, duration and dates are **derived**, not entered:

- **Duration** = span from earliest child start to latest child finish (not a sum of child durations)
- **Start** = earliest child start (but not earlier than the group's own predecessor constraints — R2)
- **Finish** = latest child finish

Groups may have predecessors (R2), which can push the group's start (and all children) later.

### R4 — Task duration entry

The user enters **duration** for each **`kind: task`** item. Duration is expected **working time**, in Microsoft Project notation (R12).

Groups and milestones have no user-entered duration — computed (group) or zero (milestone).

### R5 — Predecessor relationships

The user defines predecessor relationships using **Microsoft Project link semantics**.

**Storage format:** On `task` and `group` items, `predecessors` is **always an inline YAML list** of MS Project format strings:

```yaml
predecessors: ["5FS", "7SS+2d"]
predecessors: ["0FS"]
predecessors: ["10SS"]
```

Block-style bulleted lists must not be used.

| Component | Format | Default |
|-----------|--------|---------|
| Task reference | Integer Unique ID | — |
| Link type | `FS`, `SS`, `FF`, `SF` | `FS` |
| Lag / lead | `+3d` (lag), `-2d` (lead) | zero |

**Predecessor listing rules** — each task lists only **immediate** predecessors:

| Situation | Required predecessors |
|-----------|----------------------|
| Top-level task, no other predecessors | `["0FS"]` — task 0 only |
| Child task, no other predecessors | `["{parentId}SS"]` — parent only, start-to-start (R2) |
| Task with specific predecessors | Those predecessors only — **never** include `0FS` |

A task's predecessor list must be **either** `["0FS"]` alone **or** one or more other links with no `0FS` mixed in.

**Link types:**

| Type | Meaning |
|------|---------|
| FS | Successor cannot start until predecessor finishes (next working day after finish date; ``0FS`` from milestone starts same day) |
| SS | Successor cannot start until predecessor starts |
| FF | Successor cannot finish until predecessor finishes |
| SF | Successor cannot finish until predecessor starts |

**Milestone predecessor equivalence (R11):** When a predecessor link targets a milestone, all link types resolve to that milestone's single `date`.

### R6 — Stable Unique IDs

Task identifiers behave like Microsoft Project **Unique ID**:

- **ID 0** reserved for the project start milestone (R0)
- IDs 1+ assigned once at creation (next available integer)
- **Never automatically renumbered** when items are reordered
- Predecessor references remain valid after reordering
- Gaps in the ID sequence are acceptable after deletion
- IDs are **opaque references**, not list position — file order conveys display order

### R7 — Auto Schedule

The system automatically calculates start and finish dates from:

- Task durations (R12)
- Predecessor relationships (link type and lag/lead)
- Project start milestone (ID 0)
- Parent predecessor constraints on children (R2)
- Working calendar (R13)

The user does **not** manually set start/finish on tasks in Auto Schedule mode (R14).

Group dates roll up from children (R3). **Project finish** = latest finish among all items.

### R8 — Human-readable data store

Schedule data is **indented YAML** that:

- A user and agent can read and edit directly
- Supports version control (git diffs)
- Shows hierarchy clearly (indentation)
- **Task order** is controlled by the user and agent — never rewritten by tooling (recommended convention: `context.md` → Task order)

Non-milestone items have **no date fields** in the schedule file (R14). Computed dates appear only in engine output (Gantt, reports).

### R11 — Milestones

**`kind: milestone`** items:

- **Zero duration** (implicit — no `duration` field) and user-entered **`date`**
- Stable **Unique ID**
- **Cannot have predecessors** — only *be* predecessors of other work
- User-set **`date` is authoritative** — the engine does not override it
- **Milestones are the only mechanism** for a user-defined date constraint at a point in the schedule; other items reference that point via predecessor links
- Project start (ID 0) is a milestone (R0)

Milestone `date` values must fall on a **working day** in the calendar; otherwise validation fails with an error.

### R14 — No date fields on non-milestone items

In the schedule file, **only milestones** have a `date` field. All other timing is computed at render time, not stored in source YAML.

### R12 — Duration notation

Durations and lag/lead use **Microsoft Project suffix notation**. MVP: **days and weeks only**:

| Suffix | Meaning |
|--------|---------|
| `d` | working days |
| `w` | weeks (converted via calendar) |

Examples: `4d`, `2w`, `5FS+3d`, `7SS+1w`. A duration of `4d` means four **working** days (R13).

### R13 — Working calendar

- **Weekends:** no work on Saturday or Sunday (MVP)
- **Holidays:** no work on configured holidays (MVP)
- Schedule dates are **calendar dates**; durations are **working-day durations**
- Start/finish calculations skip non-working days when counting duration and applying lag/lead
- Calendar lives in a **separate file** referenced from the schedule (see Calendar file format)

Both files are validated before calculating.

### R15 — Validation before compute

Schedule and calendar files must conform to the **Schedule file format** and schemas. The engine validates **before** calculating — invalid files are **rejected with clear errors**. The user or agent fixes the file and retries.

### R16 — Read-only scheduling engine

The scheduling engine **never modifies** schedule or calendar files. On run it **validates**, **computes**, and **writes separate output** (JSON, Gantt artifacts, reports). Only the user and agent edit source data.

### R18 — Schedule logic errors

Impossible schedules are **hard errors**, not warnings. Examples:

- Cyclic predecessor dependencies
- Unknown predecessor IDs
- A computed or pinned schedule that **cannot satisfy a milestone date** (e.g. a task chain finishes after a milestone it must reach)
- Duplicate IDs, invalid predecessor listing (R5), milestone on a non-working day

The engine does not auto-fix or silently adjust user data.

### R19 — Task timing mode (required field)

Every **`kind: task`** item must include a **`timing`** field — never optional, never inferred:

| `timing` | User specifies | Engine computes |
|----------|----------------|-----------------|
| `auto` | `duration`, `predecessors` | `start`, `finish` |
| `start_duration` | `start`, `duration`, `predecessors` | `finish` |
| `start_finish` | `start`, `finish`, `predecessors` | `duration` |
| `finish_duration` | `finish`, `duration`, `predecessors` | `start` |

Every task must set `timing` explicitly, including `timing: auto`.

### R20 — Task date fields by timing mode

- **`auto`:** `start` and `finish` forbidden in the schedule file
- **`start_duration`:** `start` required; `finish` forbidden
- **`start_finish`:** `start` and `finish` required; `duration` forbidden
- **`finish_duration`:** `finish` required; `start` forbidden

Milestones keep authoritative **`date`**. Groups have no user-entered dates (R3 unchanged).

### R21 — Predecessors on pinned tasks

`predecessors` remain **required** in all timing modes. Pinned `start` / `finish` values are authoritative. Predecessors define earliest allowable bounds.

### R22 — Pinned-task validation

Impossible pinned schedules are **hard errors** before compute (see R18).

### R23 — Pinned-task compute

The engine derives the third field from the two user-specified fields using working-calendar math. Pinned fields are not overwritten. `auto` tasks use the existing CPM forward pass. Detail: `task_timing_modes.md`.

### R17 — Project directory

Each schedule project lives in **one directory** containing the schedule file, calendar file, and generated artifacts (Gantt, JSON). The skill asks for the schedule file path or project directory. Schedule filename is not prescribed. Calendar path is relative to the schedule file.

### R9 — Gantt chart

The schedule must be viewable as a **Gantt chart**:

- Task and group bars, milestones, **dependency links** (FS/SS/FF/SF), **critical-path highlighting**
- Regenerated when the user or agent runs a compute step
- **Interactive drag-and-drop editing is not required**

Generated viewer artifacts are written into the **project directory** alongside the schedule. Implementation details: `architecture.md`.

### R25 — Critical path

The engine identifies items on the chain that drives **project finish**. The user sees critical items in the **Gantt** and in **computed output** (for reports and agent summaries).

### R24 — View in browser

After compute, the user can **open the Gantt in a browser**:

- On the **same machine** or **remotely** (SSH with port forwarding or network URL)
- The tool prints URLs; the **user opens manually** — no auto-open browser
- The chart must be **reachable on the network** when working on a remote server (LAN, Tailscale, etc.)

CLI flags and server implementation: `architecture.md`, `decisions.md`.

### R26 — Printable Gantt

The user must be able to **print** the schedule for viewing and sharing — to a printer, PDF, or other static document. The implementation (browser print, server-generated PDF, etc.) is not prescribed, but the output must be **clean and faithful** to the on-screen Gantt: task and group names, bars, milestones, dependency links, critical-path highlighting, and timeline alignment.

### R10 — Live refresh (nice to have)

While developing a schedule, the Gantt **updates when the schedule file changes** without manual refresh.

**Status:** Shelved. See `live_refresh.md` for the implementation plan and rationale.

---

## Out of scope (MVP)

- Interactive Gantt editing (drag bars, drag links)
- Hour-based durations and lag (`8h`)
- Engine rewriting schedule file order or content
- Cross-project predecessor links
- Resource assignment / leveling
- Cost tracking
- Partial work days / custom work weeks (e.g. four-day week)
- Baselines / actuals / % complete

---

## Documentation map

| You need… | Document |
|-----------|----------|
| Hard requirements (this file) | `prd.md` |
| YAML examples and editing cheat sheet | `data_model.md` |
| How it's built (modules, CLIs, serve) | `architecture.md` |
| Resolved product & engineering choices | `decisions.md` |
| CPM algorithm steps | `scheduling_algorithm.md` |
| Glossary | `context.md` |
| Live refresh plan (shelved) | `live_refresh.md` |

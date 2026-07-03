# Project Schedule — Product Requirements Document

**Status:** MVP complete  
**Last updated:** 2026-06-14

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

Engineering choices (modules, CLIs, algorithms): `architecture.md`. The concrete file shape, field rules, and examples are defined canonically in `data_model.md`.

## Product requirements — data model

These are the product-level capabilities the data model must support, phrased as user-facing functionality. They state **what the product lets a user express and rely on**, not how the YAML is shaped — the concrete file format, field-by-field rules, and examples live in **`data_model.md`**, and the shipped JSON Schemas enforce them.

### What a schedule is made of

- **DM1 — Three item types.** A user builds a schedule from exactly three kinds of items: **milestones** (fixed points in time), **tasks** (work that takes time), and **groups** (containers that organize and roll up other items). Every item declares which kind it is.
- **DM2 — One project anchor.** Every schedule has a single project-start point that anchors all other work; the user sets its date.
- **DM3 — Arbitrary hierarchy.** Groups can contain tasks, milestones, and other groups to any depth, so a user can organize a project into phases and sub-phases.

### What the user controls vs. what the tool computes

- **DM4 — Milestones are the dependency anchor for fixed dates.** A milestone is the way a user places a fixed point in time that **other items can depend on** (e.g. a permit-approved date that downstream work keys off). Tasks can also carry committed dates for their own scheduling via timing modes (DM10), but only a milestone is a shared, dependable date anchor in the dependency graph.
- **DM5 — Durations on work, not containers.** A user gives a duration to a task (the work it represents); a group's duration and dates are **derived** from its children and never entered by hand.
- **DM6 — Computed dates are not authored.** For ordinary planning, the user never types start/finish dates onto tasks or groups; the tool computes them. (Committed task dates are available through timing modes — DM10.)

### Dependencies

- **DM7 — Dependencies on work and containers only.** Tasks and groups can depend on other items; milestones cannot depend on anything (they are fixed points others depend on). This reflects that a milestone is a target, not work to be scheduled.
- **DM8 — Microsoft Project link semantics.** Users express dependencies with the four standard MS Project link types (finish-to-start, start-to-start, finish-to-finish, start-to-finish) and optional lead/lag time, so the behavior matches what MS Project users expect.
- **DM9 — Group acts as a local start.** When a group has dependencies, none of its children can start before the group does — a group behaves as a "local project start" for its subtree.

### Committed (pinned) task dates

- **DM10 — Timing modes for execution.** Beyond plain auto-scheduling, a user can commit a task to a specific start, a specific finish, or a fixed start-and-finish window, and the tool computes the remaining field. This supports execution workflows ("the crew starts Monday") without abandoning dependency checking.
- **DM11 — Commitments are checked, not silently bent.** A committed date that conflicts with the task's dependencies is reported as an error for the user to resolve; the tool never silently moves a date the user pinned.

### Identity, ordering, and trust

- **DM12 — Stable identifiers.** Each item has a permanent identifier that does not change when items are reordered, so dependencies stay valid as the schedule evolves.
- **DM13 — User-controlled ordering.** The order of items in the schedule is controlled by the user and agent (and drives the order rows appear in the Gantt); the tool never reorders the user's file.
- **DM14 — The file is the source of truth.** The tool reads the schedule and writes only generated output; it never edits the user's schedule or calendar files.

Concrete realization of all of the above — field names, allowed/forbidden fields per kind, predecessor string format, listing rules, and worked examples — is in **`data_model.md`**.

## MVP status

**MVP is complete** (2026-06-14). Requirements **R0–R26** in this document are implemented in `skills/schedule/` except **R10 (live refresh)**, which remains shelved (`live_refresh.md`). Post-MVP work is limited to shelved nice-to-haves and items in § Out of scope (MVP) unless product scope changes.

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

## File format and validation

The concrete file shape is defined canonically in **`data_model.md`**: the schedule header (`calendar` + `items`), the three `kind` sub-schemas and their allowed/forbidden fields, item field order, the predecessor string format and listing rules, timing modes, and the calendar file shape. The product requirements those rules satisfy are above (§ Product requirements — data model); the behavioral requirements that depend on them are below (R0–R26).

Both schedule and calendar files are validated against shipped **JSON Schema** files (authored in YAML: `schemas/schedule.schema.yaml`, `schemas/calendar.schema.yaml`) — the same schemas run at compute time and, via Red Hat YAML, in the editor. Files that violate the format are **rejected with clear errors** (R15); invalid field combinations are schema errors, not runtime surprises.

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
- A **`kind`** discriminator as the **first field** (see `data_model.md`)
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

The user defines predecessor relationships using **Microsoft Project link semantics**: the four link types (FS, SS, FF, SF) with optional lead/lag, listing only **immediate** predecessors. Tasks and groups carry predecessors; milestones do not (R11). The concrete string format, listing rules, and link-type meanings are defined in `data_model.md`.

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
- **Task order** is controlled by the user and agent — never rewritten by tooling (recommended ordering convention: `data_model.md`)

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

Durations and lag/lead use **Microsoft Project suffix notation**, **days and weeks only** (no hours in MVP). A `4d` duration means four **working** days (R13). Exact notation: `data_model.md`.

### R13 — Working calendar

- **Weekends:** no work on Saturday or Sunday (MVP)
- **Holidays:** no work on configured holidays (MVP)
- Schedule dates are **calendar dates**; durations are **working-day durations**
- Start/finish calculations skip non-working days when counting duration and applying lag/lead
- Calendar lives in a **separate file** referenced from the schedule (shape in `data_model.md`)

Both files are validated before calculating.

### R15 — Validation before compute

Schedule and calendar files must conform to the file format (`data_model.md`) and schemas. The engine validates **before** calculating — invalid files are **rejected with clear errors**. The user or agent fixes the file and retries.

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

Every **`kind: task`** item must declare a **`timing`** mode explicitly — never optional, never inferred. The modes let the user auto-schedule, or commit a start, a finish, or a start-and-finish window, with the engine computing the remaining field (product capability DM10). The mode names, and which fields each requires, are defined in `data_model.md`.

### R20 — Task date fields by timing mode

The fields a task may carry depend on its `timing` mode (defined in `data_model.md`): the engine computes the field(s) the user did not commit. Milestones keep their authoritative **`date`**; groups have no user-entered dates (R3 unchanged).

### R21 — Predecessors on pinned tasks

`predecessors` remain **required** in all timing modes. Pinned `start` / `finish` values are authoritative. Predecessors define earliest allowable bounds.

### R22 — Pinned-task validation

Impossible pinned schedules are **hard errors** before compute (see R18).

### R23 — Pinned-task compute

The engine derives the third field from the two user-specified fields using working-calendar math. Pinned fields are not overwritten. `auto` tasks use the existing CPM forward pass. Detail: `task_timing_modes.md`.

### R17 — Project directory

Each schedule project lives in **one directory** containing the schedule file, calendar file, and a **`site/`** subfolder for generated viewer artifacts. The skill asks for the schedule file path or project directory. Schedule filename is not prescribed. Calendar path is relative to the schedule file.

### R9 — Gantt chart

The schedule must be viewable as a **Gantt chart**:

- Task and group bars, milestones, **dependency links** (FS/SS/FF/SF), **critical-path highlighting**
- Regenerated when the user or agent runs a compute step
- **Interactive drag-and-drop editing is not required**

Generated viewer artifacts are written into **`site/`** under the project directory (not beside the YAML source files). Implementation details: `architecture.md`.

### R25 — Critical path

The engine identifies items on the chain that drives **project finish**. The user sees critical items in the **Gantt** and in **computed output** (for reports and agent summaries).

### R24 — View in browser

After compute, the user can **open the Gantt in a browser**:

- On the **same machine** or **remotely** (SSH with port forwarding or network URL)
- The tool prints URLs; the **user opens manually** — no auto-open browser
- The chart must be **reachable on the network** when working on a remote server (LAN, Tailscale, etc.)

CLI flags and server implementation: `architecture.md`, `decisions.md`.

### R27 — Collapse and expand groups

In the Gantt viewer, the user can **collapse and expand nested groups** to control how much of the hierarchy is shown:

- Collapsing a group **hides its descendant rows** while keeping the group's own summary bar and any dependency links to or from the group
- Collapsing and expanding works at **arbitrary nesting depth** (R2, DM3), independently per group
- A single control **collapses or expands all groups** at once
- This is a **view-only** control — it never changes the schedule file, computed dates, or row order (R13)

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
| Product & behavioral requirements (this file) | `prd.md` |
| Canonical data model — file shape, fields, examples | `data_model.md` |
| How it's built (modules, CLIs, serve) | `architecture.md` |
| Resolved product & engineering choices | `decisions.md` |
| CPM algorithm steps | `scheduling_algorithm.md` |
| Glossary | `glossary.md` |
| Live refresh plan (shelved) | `live_refresh.md` |
| MVP backlog (complete) | `projects/260607_1700_project_schedule/260611_2358_remaining_tasks.md` |

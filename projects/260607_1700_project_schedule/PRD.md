# Project Schedule — Product Requirements Document

**Status:** Draft (in design)
**Last updated:** 2026-06-07

## Overview

A text-native alternative to Microsoft Project Professional Auto Schedule. The schedule lives in human-readable structured files that both a user and an AI agent can edit. A deterministic scheduling engine computes dates from durations and predecessor links on a real calendar (weekends and holidays excluded). A Gantt chart is generated as a static (optionally hot-reloaded) visual artifact.

## Design principles

1. **File is source of truth** — not a UI, not chat history
2. **Agent-native editing** — structured data the LLM can read and write reliably
3. **Deterministic scheduling** — date math is code, not LLM inference
4. **Microsoft Project semantics** — especially Auto Schedule, rollup scheduling, predecessor syntax, and duration notation

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

The project ships a **JSON Schema** describing the schedule file. The `kind` field selects a sub-schema via `oneOf`; all other fields are validated against that sub-schema only.

- The scheduling engine validates **before** calculating — invalid files are rejected with clear errors
- Editor YAML extensions may use the same schema for live squiggles (e.g. Red Hat YAML + `yaml.schemas`)
- A group with zero children is **invalid at schema level** (`children.minItems: 1`) — not merely a runtime warning

### Group kind naming

Microsoft Project calls this a **summary task**. We use **`group`** instead — shorter, avoids confusion with report/summary language, and reads naturally in YAML (`kind: group`). Other names considered and rejected: `category`, `phase`, `section`, `container`, `rollup`, `block`, `package`, `summary`.

### Examples

**Valid:**

```yaml
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

- Task durations (working days; see R12)
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
- List tasks in **hybrid order**: parent immediately above its children; siblings sorted by computed start date; top-level groups sorted by earliest child start

Non-milestone tasks have **no date fields** in the schedule file (R14). The scheduling engine computes dates for display (Gantt, reports) but does not persist `start`/`finish` on regular tasks in the source file.

### R9 — Gantt chart rendering

The schedule must be renderable as a Gantt chart view.

- Live editing of the Gantt is **not** required
- Static rendered artifact is acceptable (HTML, image, etc.)
- Regenerated on demand or when the schedule file changes

### R10 — Hot reload (nice to have)

If the Gantt is a web-page-based artifact, it should hot-reload when the underlying schedule file changes during development.

### R11 — Milestones

The system must support **milestones** (`kind: milestone`):

- A milestone has **zero duration** (implicit — no `duration` field) and a user-entered **`date`**
- A milestone has a stable **Unique ID**
- A milestone **cannot have predecessors** — it can only *be* a predecessor of other tasks
- The user-set **`date` is authoritative** — the scheduling engine does not override it; conflicts with computed constraints produce warnings
- **Milestones are the only mechanism** for applying a user-defined date constraint at a specific point in the schedule; other tasks reference that point via predecessor links
- The project start (ID 0) is a milestone — the special case that anchors the entire project (R0)

**Milestone predecessor equivalence:** When any predecessor link targets a milestone, link type does not matter — FS, SS, FF, and SF all resolve to the milestone's single `date`.

### R14 — No date fields on non-milestone items

In the schedule file, **only milestones** (`kind: milestone`) have a `date` field. All other timing is computed at render time (Gantt, reports), not stored in the source file.

### R15 — Schema validation

Schedule files must conform to the **Data model** defined above. See JSON Schema requirements under Schema validation in the Data model section.

### R12 — Duration notation

Durations and lag/lead values use **Microsoft Project style** suffix notation:

| Suffix | Meaning |
|--------|---------|
| `d` | working days |
| `w` | weeks |
| `h` | hours |

**Examples:** `4d`, `2w`, `8h`, `3d` lag in `5FS+3d`

All duration arithmetic respects the working calendar (R13) — a duration of `4d` means four working days, skipping weekends and holidays.

### R13 — Working calendar

The system must map the schedule onto a **real calendar**:

- **Weekends:** no work occurs on Saturday or Sunday (MVP)
- **Holidays:** no work occurs on configured holidays (MVP)
- Schedule dates are **calendar dates**; durations are **working-day durations**
- Start/finish calculations skip non-working days when counting duration and applying lag/lead

**Calendar file:** Holidays and calendar configuration live in a **separate file** from the schedule — not inline in the schedule YAML. The schedule file references the calendar file by path. This allows one calendar to be shared across multiple schedules.

```yaml
# schedule file (header)
calendar: ./calendar.yaml
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
- Manual schedule mode (user-fixed dates per task)
- Cross-project predecessor links (`C:\other.mpp\3FF`)
- Resource assignment / leveling
- Cost tracking
- Partial work days / custom work weeks (e.g. 4-day week)
- Baselines / actuals / % complete

---

## Open questions

- [x] File format for predecessors: list of MS Project format strings (uniform schema)
- [x] Identifier type: stable integer Unique ID; ID 0 reserved for project start
- [x] Duration units: MS Project style (`4d`, `2w`, `8h`)
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
- [x] Holiday list: separate calendar file, referenced by path from schedule file
- [ ] Manual schedule mode: needed in v1 or later?

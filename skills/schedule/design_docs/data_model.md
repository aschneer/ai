# Data Model

**Canonical definition of the schedule and calendar file shape** — field rules, predecessor format, listing rules, timing modes, and examples. The product requirements behind these rules are in `prd.md` (§ Requirements). Enforced by `schemas/schedule.schema.yaml` and `schemas/calendar.schema.yaml`. Implementation: `architecture.md`. Term definitions: `glossary.md`.

## Schedule file header

Top-level keys in order: `calendar` (path relative to schedule file), optional `people` and `events` (see [People and events](#people-and-events)), then `items`:

```yaml
calendar: calendar.yaml
people:              # optional; must appear above items
  - name: Maria
    segments:
      - {start: 2026-06-15, finish: 2026-06-26, label: On vacation}
events:              # optional; must appear above items
  - name: Company
    segments:
      - {start: 2026-07-04, finish: 2026-07-04, label: Independence Day}
items:
  - kind: milestone
    id: 0
    name: Project start
    date: 2026-06-09
  - kind: task
    ...
```

## Three kinds

`kind` is always the **first field** on every item.

### Kind comparison

| | **Milestone** | **Task** | **Group** |
|--|---------------|----------|-----------|
| **Purpose** | Pin a fixed date | Work that takes time | Roll-up container |
| **Duration** | Zero (implicit) | User-entered (`4d`) | Derived from children |
| **`date`** | User-set | Forbidden | Forbidden |
| **Predecessors** | Optional; deadline annotation only (FS, no lag) | Required for `auto`; optional for pinned modes | Optional |
| **Children** | Forbidden | Forbidden | Required (min 1) |

### Field constraints

| Field | Milestone | Task | Group |
|-------|-----------|------|-------|
| `kind` | `milestone` | `task` | `group` |
| `id` | required | required | required |
| `name` | required | required | required |
| `date` | required | forbidden | forbidden |
| `type` | optional (`project_finish`) | forbidden | forbidden |
| `timing` | forbidden | required | forbidden |
| `duration` | forbidden | conditional | forbidden |
| `start` / `finish` | forbidden | conditional | forbidden |
| `predecessors` | optional (FS only, no lag) | conditional | optional |
| `percent_complete` | forbidden | required (0–100) | forbidden |
| `children` | forbidden | forbidden | required (min 1) |

### Field order

`kind` is always first, then `id`, then the remaining fields for that kind:

```yaml
- kind: task
  id: 11
  name: Trim the hedges
  timing: auto
  duration: 2d
  predecessors: ["10SS"]
  percent_complete: 0
```

## Task progress (`percent_complete`)

Every task carries a **required** integer `percent_complete` (0–100). It is the fraction of the task that is done and renders as a darker progress fill on the Gantt bar (Microsoft Project style); `100` fills the bar completely. It is **task-only** — forbidden on milestones and groups (groups show progress through their child bars, not a rolled-up value). Write `0` on any new or not-started task; raise it only when the user reports progress. It never affects dates, the critical path, or project finish.

## ID 0 — project start

Every schedule must include a project start milestone:

```yaml
- kind: milestone
  id: 0
  name: Project start
  date: 2026-06-09
```

ID 0 is reserved. IDs 1+ are assigned at creation and **never renumbered** when items are reordered.

## Predecessors

Always an **inline** list of MS Project format strings (never a block-style bulleted list):

```yaml
predecessors: ["0FS"]
predecessors: ["5FS", "7SS+2d"]
predecessors: ["10SS"]
```

A predecessor list is **either** `["0FS"]` alone **or** one or more other links with no `0FS` mixed in (see Listing rules below).

**Predecessors are not always required.** An item needs a predecessor only when it cannot place itself:

- **`auto` tasks require** at least one predecessor — duration alone gives no dates, so they need an anchor.
- **Pinned tasks** (`start_duration`, `start_finish`, `finish_duration`) and **groups** may omit predecessors — a pinned task sets its own dates; a group rolls up from its children.

Omit predecessors entirely for a self-anchoring item that has no real dependency (do **not** write `["0FS"]` or `["{parentId}SS"]` as a placeholder). An item with no predecessors draws **no dependency arrow** in the Gantt viewer. A self-anchoring item **may** still list real predecessors when it has them — those draw arrows and constrain its earliest bounds as usual.

| Component | Format | Default |
|-----------|--------|---------|
| Task reference | Integer Unique ID | — |
| Link type | `FS`, `SS`, `FF`, `SF` | `FS` |
| Lag / lead | `+3d`, `-2d`, `+1w` | zero |

### Listing rules

When an item **has** predecessors, list them by these rules (a self-anchoring item with no dependency omits the field — see above):

| Situation | Required predecessors |
|-----------|----------------------|
| Top-level, no other preds | `["0FS"]` |
| Child, no other preds | `["{parentId}SS"]` |
| Has specific preds | Those only — never include `0FS` |
| Self-anchoring (pinned task / group), no dependency | Omit `predecessors` |
| Milestone deadline (culminating chain) | The last task, FS only, no lag: `["{taskId}FS"]` |

Only **immediate** predecessors. No transitive chain.

### Milestone deadline predecessors

A milestone may list a predecessor to mark that a chain of work **culminates in that fixed date** (a deadline). The rules are narrower than for tasks and groups:

- **Finish-to-start only, no lag** — e.g. `["42FS"]`. Any other link type, or a lag, is a validation error: the milestone's `date` is authoritative, so the link has no schedulable meaning and would only mislead.
- **Never `0FS`, never self-referential.**
- **Annotation only** — the predecessor never moves the milestone. It draws the dependency link in the Gantt and, when the chain finishes exactly on the date (zero slack), puts the milestone and its driving chain on the critical path.
- **Deadline enforcement** — if the predecessor chain finishes **after** the milestone date, the deadline is unreachable and validation fails (a hard error; see `prd.md` §6.7 / §3.8).
- **Not critical on its own** — a plain deadline milestone never marks its chain critical. Only a designated **project-finish** milestone does (see below).

### Project-finish milestone

One milestone may be designated the project's finish with `type: project_finish`:

- **At most one** per schedule (two = a hard error).
- **Predecessors required** — it must list the culminating chain (FS only, no lag, like any milestone deadline).
- Its `date` is the project **deadline**. The **critical path** is the zero-slack chain feeding it: critical when the chain finishes exactly on the date, **empty** when the chain finishes early (buffer).
- The reported **project finish** is when the feeding work actually completes — possibly **earlier** than the milestone date (the deadline is shown separately as the milestone marker). This matches Microsoft Project.
- With no designated milestone, project finish is the latest computed finish and the critical path is the longest path to it (unchanged default).

```yaml
- kind: milestone
  id: 50
  name: Launch
  date: 2026-06-19
  type: project_finish
  predecessors: ["42FS"]
```

### Link types

| Type | Meaning |
|------|---------|
| FS | Successor cannot start until predecessor finishes |
| SS | Successor cannot start until predecessor starts |
| FF | Successor cannot finish until predecessor finishes |
| SF | Successor cannot finish until predecessor starts |

**FS start day.** With zero lag, an FS successor of a **task or group** starts the **next working day** after the predecessor's finish — the predecessor occupies its finish day, so the successor cannot begin until the day after. An FS successor of a **milestone** (including `0FS` from project start) starts **on** the milestone date itself. This matches Microsoft Project: a zero-duration milestone is an instantaneous point at the *start* of its day, so its FS successor begins the same day. To push a milestone's successor to the next day instead, add lag — e.g. `13FS+1d`. Positive lag counts working days from the finish for either kind.

**Milestone targets:** because a milestone's start and finish are the same date, all link types (FS/SS/FF/SF) resolve to that single `date`.

**Milestone on a working day:** milestone `date` values must fall on a working day in the calendar file. Validation fails with an error if not — move the date to a working day before computing.

## Task timing

Every **`kind: task`** item requires **`timing`**:

| `timing` | User specifies | Optional | Engine computes |
|----------|----------------|----------|-----------------|
| `auto` | `duration`, `predecessors` | — | `start`, `finish` |
| `start_duration` | `start`, `duration` | `predecessors` | `finish` |
| `start_finish` | `start`, `finish` | `predecessors` | `duration` |
| `finish_duration` | `finish`, `duration` | `predecessors` | `start` |

Only `auto` requires `predecessors`; the pinned modes may omit them (see Predecessors above).

```yaml
- kind: task
  id: 11
  name: Trim the hedges
  timing: auto
  duration: 2d
  predecessors: ["10SS"]
```

Pinned `start` / `finish` values are authoritative; predecessors define earliest allowable bounds. Violations are hard errors before compute.

## Durations

Days and weeks only: `4d`, `2w`. No hours. Lag uses the same units (`5FS+3d`, `7SS+1w`).

## Item order

The order of items in the file is controlled by the user and agent — the engine never rewrites it — and is also the **Gantt row order** (top-to-bottom timeline). Recommended convention: order items as a coherent date sequence rather than grouped by kind — each parent group directly above its children, top-level siblings by computed start date, and milestones inline where they fall (not stacked at the top).

## Groups

- Duration = span earliest child start → latest child finish (not sum of child durations)
- Predecessors are **optional** — with none, the group simply spans its children
- A predecessor, when present, constrains when children may start (local project start)
- An `auto` child with no real dependency uses `{parentId}SS`; a pinned child with no dependency omits `predecessors`

## People and events

Two optional decorative bands drawn above the schedule — labeled date-range segments that give a viewer context without affecting the schedule. **Pure annotation:** neither has IDs or predecessors, and neither affects scheduling, the critical path, or project finish. Both use the **identical shape** (`name` + `segments`) and both must appear **above** `items`.

- **`people`** — one row per person: availability, vacation, out-of-office, work location by date.
- **`events`** — calendar context not tied to a person: company events, holidays of note, external dates.

```yaml
people:
  - name: Maria
    segments:
      - {start: 2026-05-11, finish: 2026-05-15, label: Out of office}
      - {start: 2026-06-15, finish: 2026-06-26, label: On vacation}
  - name: Dev
    segments:
      - {start: 2026-05-04, finish: 2026-05-29, label: Traveling}
events:
  - name: Company
    segments:
      - {start: 2026-07-04, finish: 2026-07-04, label: Independence Day}
      - {start: 2026-09-19, finish: 2026-09-20, label: County fair}
```

- Each entry: `name` and `segments` (min 1).
- Each segment: `start`, `finish`, `label` — **all required**.
- Segments use **any calendar day** (weekends and holidays allowed, unlike task durations); `finish` is **inclusive**.
- Segments within one band **must not overlap** — a hard validation error.
- The viewer renders **people rows on top, events below**, in two distinct colors (see the legend), extends its date axis to include both, and offers a single lock toggle that pins both bands below the header while scrolling.

## Calendar file

A separate YAML file referenced by the schedule's `calendar` path. Both keys are **required**:

```yaml
weekends: [sat, sun]       # required; one or more of mon, tue, wed, thu, fri, sat, sun
holidays:                  # required; ISO dates excluded as non-working days (may be an empty list: [])
  - 2026-07-04
  - 2026-12-25
```

Weekends and holidays are the **non-working days**. Durations and lag count working days only, and every milestone `date` must fall on a working day (else validation fails).

## Valid example

A complete, self-contained schedule (every referenced id is defined). For larger, runnable schedules see `examples/farmers_market/` and `examples/farmers_market_full/`; regression tests use `tests/fixtures/home_renovation/` (do not point tests at `examples/`).

```yaml
calendar: calendar.yaml
items:
  - kind: milestone
    id: 0
    name: Planning kickoff
    date: 2026-05-04

  - kind: group
    id: 20
    name: Vendor recruitment
    predecessors: ["0FS"]
    children:
      - kind: task
        id: 21
        name: Draft vendor prospectus
        timing: auto
        duration: 1w
        predecessors: ["20SS"]

      - kind: task
        id: 22
        name: Confirm anchor vendors
        timing: start_duration
        start: 2026-05-18
        duration: 2w
        predecessors: ["21FS"]

  - kind: task
    id: 42
    name: Send press release
    timing: auto
    duration: 2d
    predecessors: ["22FS+3d"]

  # Deadline milestone: the press release culminates in a launch date.
  - kind: milestone
    id: 50
    name: Launch deadline
    date: 2026-06-19
    predecessors: ["42FS"]
```

## Invalid examples

```yaml
items:
  # milestone: no name; predecessor must be FS with no lag (SS is invalid)
  - kind: milestone
    id: 99
    date: 2026-06-15
    predecessors: ["12SS"]

  # task: no date
  - kind: task
    id: 100
    duration: 2d
    date: 2026-06-15
    predecessors: ["0FS"]

  # group: must have at least one child
  - kind: group
    id: 101
    name: Empty group
    predecessors: ["0FS"]
    children: []
```

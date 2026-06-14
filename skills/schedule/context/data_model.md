# Data Model

**Canonical definition of the schedule and calendar file shape** — field rules, predecessor format, listing rules, timing modes, and examples. The product requirements behind these rules are in `prd.md` (§ Product requirements — data model); the behavioral requirements that build on them are `prd.md` R0–R26. Enforced by `schemas/schedule.schema.yaml` and `schemas/calendar.schema.yaml`. Implementation: `architecture.md`. Term definitions: `glossary.md`.

## Schedule file header

Optional calendar reference (path relative to schedule file). Schedule items live under `items`:

```yaml
calendar: calendar.yaml
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
| **Predecessors** | Forbidden | Required | Required |
| **Children** | Forbidden | Forbidden | Required (min 1) |

### Field constraints

| Field | Milestone | Task | Group |
|-------|-----------|------|-------|
| `kind` | `milestone` | `task` | `group` |
| `id` | required | required | required |
| `name` | required | required | required |
| `date` | required | forbidden | forbidden |
| `timing` | forbidden | required | forbidden |
| `duration` | forbidden | conditional | forbidden |
| `start` / `finish` | forbidden | conditional | forbidden |
| `predecessors` | forbidden | required | required |
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
```

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

| Component | Format | Default |
|-----------|--------|---------|
| Task reference | Integer Unique ID | — |
| Link type | `FS`, `SS`, `FF`, `SF` | `FS` |
| Lag / lead | `+3d`, `-2d`, `+1w` | zero |

### Listing rules

| Situation | Required predecessors |
|-----------|----------------------|
| Top-level, no other preds | `["0FS"]` |
| Child, no other preds | `["{parentId}SS"]` |
| Has specific preds | Those only — never include `0FS` |

Only **immediate** predecessors. No transitive chain.

### Link types

| Type | Meaning |
|------|---------|
| FS | Successor cannot start until predecessor finishes (next working day; ``0FS`` same day) |
| SS | Successor cannot start until predecessor starts |
| FF | Successor cannot finish until predecessor finishes |
| SF | Successor cannot finish until predecessor starts |

**Milestone targets:** all link types resolve to the milestone's single `date`.

**Milestone on a working day:** milestone `date` values must fall on a working day in the calendar file. Validation fails with an error if not — move the date to a working day before computing.

## Task timing

Every **`kind: task`** item requires **`timing`**:

| `timing` | User specifies | Engine computes |
|----------|----------------|-----------------|
| `auto` | `duration`, `predecessors` | `start`, `finish` |
| `start_duration` | `start`, `duration`, `predecessors` | `finish` |
| `start_finish` | `start`, `finish`, `predecessors` | `duration` |
| `finish_duration` | `finish`, `duration`, `predecessors` | `start` |

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
- May have predecessors — constrains when children may start (local project start)
- Child with no preds uses `{parentId}SS`

## Calendar file

```yaml
weekends: [sat, sun]
holidays:
  - 2026-07-04
  - 2026-12-25
```

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
```

## Invalid examples

```yaml
items:
  # milestone: no predecessors, duration, or children
  - kind: milestone
    id: 99
    date: 2026-06-15
    predecessors: ["12FS"]

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

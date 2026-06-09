# Data Model

Quick reference for editing schedule YAML. Full requirements: `prd.md`. Glossary: `context.md`. File structure is defined by JSON Schema files written in YAML (`schemas/schedule.schema.yaml`, `schemas/calendar.schema.yaml`).

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
| `duration` | forbidden | required | forbidden |
| `predecessors` | forbidden | required | forbidden |
| `children` | forbidden | forbidden | required (min 1) |

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

Inline list of MS Project format strings only:

```yaml
predecessors: ["0FS"]
predecessors: ["5FS", "7SS+2d"]
predecessors: ["10SS"]
```

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
| FS | Successor cannot start until predecessor finishes |
| SS | Successor cannot start until predecessor starts |
| FF | Successor cannot finish until predecessor finishes |
| SF | Successor cannot finish until predecessor starts |

**Milestone targets:** all link types resolve to the milestone's single `date`.

## Durations

Days and weeks only: `4d`, `2w`. No hours. Lag uses the same units (`5FS+3d`, `7SS+1w`).

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

# Task Timing Modes

**Status:** Implemented  
**Last updated:** 2026-07-04  
**Related:** `prd.md` (§5), `architecture.md`, `data_model.md`, `scheduling_algorithm.md`

## Summary

Add a required **`timing`** field on every **`kind: task`** item. The field declares which two of start, finish, and duration are user-specified; the engine computes the third. This supports project execution workflows where tasks are pinned to calendar dates (e.g. “technician starts Monday”) while keeping groups as computed roll-up containers.

**Scope:** Minor extension of the existing validate → compute pipeline — not a rewrite. Milestones, groups, predecessor syntax, calendar math, and the CPM forward pass stay as they are. Changes are localized to task schema, task-specific validation rules, and a branch in task scheduling.

**Explicit non-goals for this feature:**

- Fixed dates on groups (use milestone + predecessor on the group instead)
- YAML file layout changes (`items:` list stays)
- Hour-based durations
- Optional/default `timing` values — every task must set `timing` explicitly, including `auto`
- Backward compatibility with schedules that omit `timing`

---

## Motivation

The MVP model requires every task to use **`timing: auto`**: duration + predecessors → computed start and finish. That is enough for initial planning but not for ongoing execution, where people often commit to specific start or finish dates.

**Milestones** remain the mechanism for external events and phase gates. **Task timing modes** cover commitments on work items themselves.

| Situation | Mechanism |
|-----------|-----------|
| Normal planning task | `timing: auto` |
| “Starts Monday” | `timing: start_duration` + `start` |
| “Must finish by Friday” | `timing: finish_duration` + `finish` |
| “Runs Mon–Wed exactly” | `timing: start_finish` |
| External event / phase gate | Milestone + predecessor (on task or group) |

Groups stay floating containers: start = `max(predecessor anchor, earliest child start)`; finish = latest child finish. No user-entered dates on groups.

---

## Field design

### `timing` (required on every task)

String enum — **must always be present**; never inferred from other fields.

| Value | User specifies in file | Optional | Engine computes |
|-------|------------------------|----------|-----------------|
| `auto` | `duration`, `predecessors` | — | `start`, `finish` |
| `start_duration` | `start`, `duration` | `predecessors` | `finish` |
| `start_finish` | `start`, `finish` | `predecessors` | `duration` (working days) |
| `finish_duration` | `finish`, `duration` | `predecessors` | `start` |

**Only `auto` requires predecessors** (duration alone gives no anchor). A pinned mode sets its own dates, so predecessors are **optional** there — list them when a real dependency exists (they constrain earliest allowable bounds), omit them for a self-anchoring task (no dependency arrow drawn). See `prd.md` §3.4.

### Date fields on tasks

- **`start`** and **`finish`**: ISO dates (`YYYY-MM-DD`); allowed only when `timing` requires them.
- Milestones keep a single authoritative **`date`** field (unchanged).

### Predecessors

**Required only for `auto` tasks.** Pinned modes (`start_duration`, `start_finish`, `finish_duration`) may omit predecessors — they self-anchor via their pinned dates. When present, listing rules (`0FS`, `{parentId}SS`, etc.) are unchanged.

**Conflict policy:** Fixed `start` / `finish` in the file are authoritative. Predecessors define **earliest allowable** bounds. If a pin violates those bounds, **validation fails with a hard error** — the user fixes the schedule before compute runs. Compute does not adjust pins or resolve conflicts.

---

## Schema rules

JSON Schema uses conditional subschemas (`oneOf` / `if-then`) on the task definition:

| `timing` | Required | Optional | Forbidden |
|----------|----------|----------|-----------|
| `auto` | `kind`, `id`, `name`, `timing`, `duration`, `predecessors` | — | `start`, `finish` |
| `start_duration` | `kind`, `id`, `name`, `timing`, `start`, `duration` | `predecessors` | `finish` |
| `start_finish` | `kind`, `id`, `name`, `timing`, `start`, `finish` | `predecessors` | `duration` |
| `finish_duration` | `kind`, `id`, `name`, `timing`, `finish`, `duration` | `predecessors` | `start` |

`kind` remains the first field and is always required (unchanged).

---

## Logic validation (new checks)

Run after existing checks (duplicate IDs, predecessor refs, cycles, listing rules, milestone working days).

1. **Start lower bound** (`start_duration`, `start_finish`): compute `earliest_start` from predecessors using the same link-type math as compute. Error if `task.start < earliest_start`.

2. **Finish lower bound** (`finish_duration`): compute `earliest_finish` from predecessors. Error if `task.finish < earliest_finish`.

3. **`start_finish` sanity:** `start` ≤ `finish` on the working calendar; derived working-day duration ≥ 1.

4. **Parent floor:** pinned `start` must be ≥ the parent group’s effective earliest start (predecessor anchor or rolled-up start). Error if violated — user adjusts pin, predecessors, or milestone gates.

Validation only — no warnings channel, no auto-fix.

---

## Compute changes

**`auto` tasks:** existing `_schedule_task` behavior (unchanged).

**Pinned tasks:** read authoritative fields from file, derive the third via calendar math. **Do not overwrite** pinned fields on later fixed-point iterations.

| `timing` | Compute |
|----------|---------|
| `start_duration` | `start` ← file; `finish` ← `start + duration` |
| `start_finish` | `start`, `finish` ← file; duration derived for output |
| `finish_duration` | `finish` ← file; `start` ← back-calculate from duration |

**Groups and milestones:** no changes.

---

## Scope of code changes

> Historical — the original implementation estimate, kept for audit. The feature shipped 2026-06-14; the tables below describe the pass as planned, not remaining work.

| Area | Change size | Notes |
|------|-------------|-------|
| `schemas/schedule.schema.yaml` | Small | Required `timing`; conditional task fields |
| `logic_validate_lib.py` | Medium | New bound checks for pinned tasks |
| `compute_lib.py` | Small–medium | Branch in `_schedule_task`; immutability for pins |
| `gantt_lib.py` / JSON output | Trivial | May expose `timing` in output (optional) |
| Tests | Medium | New cases + update every task in fixtures to include `timing: auto` |
| Examples | Small | Add `timing: auto` everywhere; optional pinned-task example |
| Docs / SKILL.md | Small | Agent guidance for mode selection |

**Not touched:** group rollup, milestone handling, predecessor parsing, calendar lib, CLI entry points, Gantt viewer (except optional display of pins).

**Estimated effort:** One focused implementation pass — comparable to adding logic validation rules or Gantt JSON fields, not a ground-up redesign.

---

## Examples

### Auto (default planning mode)

```yaml
- kind: task
  id: 11
  name: Trim the hedges
  timing: auto
  duration: 2d
  predecessors: ["10SS"]
```

### Execution: fixed start

```yaml
- kind: task
  id: 42
  name: Technician on-site
  timing: start_duration
  start: 2026-06-16
  duration: 1d
  predecessors: ["15FS"]
```

### Phase gate via milestone (group unchanged)

```yaml
- kind: milestone
  id: 15
  name: Phase 2 begins
  date: 2026-06-16

- kind: group
  id: 20
  name: Phase 2
  predecessors: ["15FS"]
  children:
    - kind: task
      id: 21
      name: First task in phase
      timing: auto
      duration: 3d
      predecessors: ["20SS"]
```

---

## Implementation order

> Historical — the order the shipped pass followed.

1. `prd.md` §5 requirements (this document adds algorithm and validation detail)
2. JSON Schema — required `timing`, conditional fields
3. Update all test fixtures and examples with explicit `timing: auto`
4. Logic validation — predecessor bounds, parent floor, `start_finish` sanity
5. Compute — pinned task branches
6. `data_model.md`, `scheduling_algorithm.md`, `glossary.md`, `SKILL.md`
7. Eval cases for pinned tasks and validation errors

---

## Deferred (not part of this feature)

- Fixed dates on groups
- YAML root restructuring
- Hour durations
- Forbidding predecessors on pinned tasks
- Soft warnings or automatic pin adjustment

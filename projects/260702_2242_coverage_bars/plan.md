# Coverage Bars — Implementation Plan

Ordered task list. Design rules live in the schedule skill docs
(`skills/schedule/context/{prd,data_model}.md`, `SKILL.md`) and are updated as
part of this work. This doc tracks order and status only.

Status: `[ ]` todo · `[~]` in progress · `[x]` done

## Goal

Graph staff availability alongside the Gantt: one horizontal **Coverage** band per
person, split into labeled date-range segments on a single line (e.g. "Out of office",
"In Santa Clara", "On vacation"). Pure decoration — no predecessors, no arrows, no
effect on scheduling or the critical path.

## Model

Concise summary; full reasoning and trade-offs in **`decisions.md`** (this folder).

- New primitive, **not** an item `kind`. Lives at the **root** `coverage:` key.
- Each entry: `name` + `segments`; each segment `{start, finish, label}`, all required.
- **No IDs** (add later if needed). **No overlapping** segments per person → hard error.
- Segments use **calendar days** (any day, weekends included); `finish` inclusive.
- **Pure annotation** — never affects compute, `project_finish`, or critical path.
- Rendered as a band **above** the task rows; date axis **extends** to include coverage.
- One **neutral color**, distinct from existing chart colors, added to the **legend**.
- Labels **truncate** with a hover **tooltip** for the full text.
- `coverage:` is **optional** — schedules without it are unchanged.

## Phase 1 — Schema + validation
- [x] `schedule.schema.yaml`: added optional root `coverage` array; entry `{name, segments}`;
      segment `{start, finish, label}` (all required, ISO dates). No `items` change.
- [x] `logic_validate_lib.py`: `_check_coverage_segments` — per-person **overlap** → hard
      error (inclusive finish); calendar-day (no working-day rule). Coverage skipped by all
      existing item checks (not in `items`).
- [x] `start <= finish` per segment enforced.

## Phase 2 — Compute pass-through
- [x] `compute_lib.py`: `ComputedSchedule.coverage` carries raw coverage from input to the
      output payload untouched. `project_finish` stays work-only.
- [x] Confirmed coverage never enters CPM, rollup, or critical-path logic (it is never
      flattened into `ctx.items`). Regression test added.

## Phase 3 — Tests
- [x] Coverage validates: well-formed entry passes (+ weekend-spanning segments).
- [x] Overlapping segments per person → hard error.
- [x] `start > finish` segment → error.
- [x] Segment missing `label` → schema error.
- [x] Coverage does not change `project_finish`, and round-trips verbatim (regression test).
- [x] Schedule with no `coverage` key still valid (optional).
- [x] Existing suite passes (60 total).

## Phase 4 — Viewer
- [x] `gantt.js`: reads `coverage`; `renderCoverageBand` renders a band **above** task rows —
      one row per person, HTML segment boxes positioned via shared `spanMetrics` (extracted
      from `itemMetrics`), label inside.
- [x] Labels truncate (CSS ellipsis); full text in a `title` tooltip.
- [x] `dateRange(items, coverage)` includes coverage segments.
- [x] `gantt_theme.css` `--color-coverage` (#2a9d8f, distinct); **legend** entry added.
- [~] Coexists with collapse/expand + resizer — band is above task rows, shares the label
      column; visual confirmation pending user render.

## Phase 5 — Docs
- [ ] `data_model.md`: `coverage` root key, entry/segment shape, calendar-day rule, no-overlap.
- [ ] `prd.md`: new requirement — decorative coverage band, pure annotation, never affects CPM.
- [ ] `SKILL.md`: when/how to author coverage; that it is optional and non-scheduling.
- [ ] `README.md`: coverage in the file-shape section if it documents schedule structure.

## Phase 6 — Example + manual check
- [x] Added a `coverage:` section (2 people, 5 labeled segments) to `farmers_market_full`.
- [~] `uv run compute` clean; validated + coverage in payload. Visual confirmation (band
      above chart, truncate+tooltip, axis extends, legend color, finish unchanged) pending
      user render.

## Phase 7 — Review
- [ ] Update project folder each phase; stop before each commit for user review.

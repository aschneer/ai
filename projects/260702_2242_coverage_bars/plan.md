# Coverage Bars — Implementation Plan

Ordered task list. Design rules live in the schedule skill docs
(`skills/schedule/context/{prd,data_model}.md`, `SKILL.md`) and are updated as
part of this work. This doc tracks order and status only.

Status: `[ ]` todo · `[~]` in progress · `[x]` done

**PROJECT COMPLETE.** Schema, validation, compute pass-through, viewer band +
lock, docs, and example all shipped.

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
- [x] Coexists with collapse/expand + resizer — band is above task rows, shares the label column.
- [x] Header z-index fix: row labels tuck behind the sticky header on vertical scroll.
- [x] Coverage lock toggle (🔓/🔒 on the divider row, right edge of the label column): locked
      pins the coverage band directly below the header while scrolling; unlocked scrolls away.
      State persists across re-renders.

## Phase 5 — Docs
- [x] `data_model.md`: header order (`coverage` above `items`) + `## Coverage` section
      (entry/segment shape, calendar-day rule, inclusive finish, no-overlap, lock).
- [x] `prd.md`: DM16 (decorative availability) + R28 (coverage band render).
- [x] `SKILL.md`: file section order + coverage authoring subsection.
- [x] `README.md`: coverage note in the schedule-file section.
- [x] `glossary.md`: Coverage and Coverage segment terms.

## Phase 6 — Example + manual check
- [x] Added a `coverage:` section (2 people, 5 labeled segments) to `farmers_market_full`,
      authored above `items`.
- [x] `uv run compute` clean; user confirmed the rendered band, lock/scroll behavior,
      divider, padding, and legend.

## Phase 7 — Review
- [x] Updated project folder each phase; stopped before each commit for user review.

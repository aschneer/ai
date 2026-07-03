# Coverage Bars — Status

**Status:** In progress — Phases 1–4 + 6 code done (pending user visual check); Phase 5 (docs) next.

## Current state

Coverage is a new, decoration-only primitive at the root `coverage:` key — one
labeled band per person, non-overlapping calendar-day segments, no IDs, no
dependencies, no effect on scheduling or the critical path.

Phase 1 (schema + validation) done: optional root `coverage` array in the
schema; `_check_coverage_segments` validates `start <= finish` and rejects
overlapping segments per person (inclusive finish, any calendar day).

Phase 2 (compute pass-through) done: `ComputedSchedule.coverage` carries raw
coverage into the output payload untouched; a regression test confirms
far-future coverage does not move `project_finish` and coverage round-trips
verbatim.

Phase 3 (tests) done: 6 coverage validation tests plus the compute regression;
60 tests pass.

Phase 4 (viewer) + Phase 6 (example) code done: `renderCoverageBand` draws a
teal band above the task rows (one row per person, HTML segment boxes via shared
`spanMetrics`, truncate + `title` tooltip); `dateRange` extends to coverage;
`--color-coverage` token + legend entry added; the `farmers_market_full` example
gained a `coverage:` section (2 people, 5 segments). Deploy + validate clean.
Awaiting the user's visual confirmation of the rendered band.

Remaining: Phase 5 docs (data_model, prd, SKILL, README).

Phase-by-phase status: `plan.md`. Full locked design: `decisions.md`.

## Where things live

| What | Where |
|------|-------|
| Skill source | `skills/schedule/` |
| Schemas | `skills/schedule/schemas/schedule.schema.yaml` |
| Logic validation | `skills/schedule/src/schedule/logic_validate_lib.py` |
| Compute (pass-through) | `skills/schedule/src/schedule/compute_lib.py` |
| Gantt viewer | `skills/schedule/src/schedule/assets/gantt.js`, `gantt.html`, `gantt_theme.css` |
| Design docs (PRD, data model, glossary) | `skills/schedule/context/` |
| Implementation plan, decisions, status | `projects/260702_2242_coverage_bars/` |

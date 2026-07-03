# Coverage Bars — Status

**Status:** In progress — Phase 1 done, Phase 2 (compute pass-through) next.

## Current state

Coverage is a new, decoration-only primitive at the root `coverage:` key — one
labeled band per person, non-overlapping calendar-day segments, no IDs, no
dependencies, no effect on scheduling or the critical path.

Phase 1 (schema + validation) done: optional root `coverage` array in the
schema; `_check_coverage_segments` validates `start <= finish` and rejects
overlapping segments per person (inclusive finish, any calendar day). 53 tests
still pass. Remaining: compute pass-through, tests, viewer band, docs, example.

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

# Coverage Bars — Status

**Status:** Planned. Not started.

## Current state

Feature scoped and interviewed; model and plan locked (`plan.md`, `decisions.md`).
No code written yet.

Coverage is a new, decoration-only primitive at the root `coverage:` key — one
labeled band per person, non-overlapping calendar-day segments, no IDs, no
dependencies, no effect on scheduling or the critical path. Compute passes it
through untouched; the work is in the viewer (a band above the Gantt with
truncate+tooltip labels, a distinct legend color, and a date axis extended to
include coverage). Independent of the hour-durations and optional-predecessors
work.

Ready to implement Phase 1 (schema + validation). Nothing committed; user
reviews before each commit.

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

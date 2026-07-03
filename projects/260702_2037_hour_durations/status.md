# Hour Durations — Status

**Status:** Deferred. Planned but not started — paused intentionally, to resume later.

## Current state

Feature scoped and interviewed; model and plan locked. No code written yet.

The change threads a sub-day granularity through the temporal core, which today
is entirely calendar-day (`date`) based. Internal position becomes a
`(date, minutes_into_day)` integer pair; output stays date-only. Hours apply
**only to `auto` tasks**, are strictly sub-day, and pack into a day up to a
required `hours_per_day` calendar field before spilling (no task splitting).
Pinned tasks and milestones stay date-only. The Gantt keeps day columns and
renders hour tasks as fractional bars.

Ready to implement Phase 1 (duration + calendar grammar). Nothing committed;
user reviews before each commit.

Phase-by-phase status and the full locked model: `plan.md`.

## Where things live

| What | Where |
|------|-------|
| Skill source | `skills/schedule/` |
| Duration/lag parser | `skills/schedule/src/schedule/predecessors_lib.py` |
| Working-time math | `skills/schedule/src/schedule/calendar_lib.py` |
| Scheduling engine | `skills/schedule/src/schedule/compute_lib.py` |
| Schemas | `skills/schedule/schemas/` |
| Gantt viewer | `skills/schedule/src/schedule/assets/gantt.js` |
| Design docs (PRD, data model, glossary) | `skills/schedule/context/` |
| Implementation plan + status | `projects/260702_2037_hour_durations/` |

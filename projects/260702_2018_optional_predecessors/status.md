# Optional Predecessors — Status

**Status:** In progress — Phases 1–4 done, Phase 5 (example + manual check) next.

## Current state

Schema, tests, and docs complete and committed:

- Schema makes `predecessors` optional for the three pinned task modes and for
  groups; `auto` tasks still require one. Enforcement is schema-only — logic and
  compute already tolerate empty predecessors (verified, no change).
- 7 tests added (53 pass). One documents the accepted lone-critical floater edge.
- `data_model.md`, `prd.md` (new DM15 + R9 note), and `SKILL.md` updated.

Remaining: add a no-pred availability group to the `farmers_market_full` example
and confirm compute is clean with no arrows on the floaters.

Phase-by-phase status: `plan.md`.

## Where things live

| What | Where |
|------|-------|
| Skill source | `skills/schedule/` |
| Schema (enforcement point) | `skills/schedule/schemas/schedule.schema.yaml` |
| Design docs (PRD, data model, glossary) | `skills/schedule/context/` |
| Implementation plan + status | `projects/260702_2018_optional_predecessors/` |

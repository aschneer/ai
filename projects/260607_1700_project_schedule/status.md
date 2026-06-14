# Project Schedule — Status

**Status:** MVP complete  
**Completed:** 2026-06-14

## Summary

The Schedule skill is implemented and meets MVP requirements. Users and agents edit YAML schedule files; the library validates, runs CPM, and renders a static Gantt chart.

## What shipped

- JSON Schema + logic validation (fail-fast before compute)
- CPM compute with critical path, group rollup, task timing modes
- CLIs: `validate`, `compute`
- Static Gantt viewer with dependency lines and accessible color theme
- Agent skill (`skills/schedule/SKILL.md`) and evals
- Examples: `farmers_market`, `farmers_market_full`

## Requirements coverage

All PRD requirements **R0–R26** are implemented except **R10 (live refresh)**, which is shelved. See `skills/schedule/context/prd.md` § MVP status.

## Not in MVP (unchanged)

- Live Gantt hot reload — shelved (`skills/schedule/context/live_refresh.md`)
- Interactive Gantt editing, resource leveling, hours, baselines, etc. — out of scope (`skills/schedule/context/prd.md` § Out of scope)

## Where things live

| What | Where |
|------|--------|
| Implementation | `skills/schedule/` |
| Canonical PRD & docs | `skills/schedule/context/` |
| Design notes (this project) | `projects/260607_1700_project_schedule/` |
| MVP backlog (closed) | `260611_2358_remaining_tasks.md` |

## Post-MVP

No active development backlog. Revisit shelved or out-of-scope items only if product scope changes.

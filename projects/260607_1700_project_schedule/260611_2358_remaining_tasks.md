# Schedule Skill — Remaining Tasks

**Created:** 2026-06-11 23:58  
**Status:** MVP complete (2026-06-14)  
**Skill location:** `skills/schedule/`  
**Design docs:** `projects/260607_1700_project_schedule/`, `skills/schedule/context/`

## MVP complete

All MVP requirements (PRD R0–R26) are implemented except **R10 live refresh**, which remains shelved. There is no active MVP backlog.

Final MVP work completed after the original backlog was written:

- R18 milestone reachability validation (`validate_milestone_reachability`)
- Accessible Gantt color theme (`gantt_theme.css`)
- Gantt viewer polish (multi-row header, freeze panes, dependency lines, critical path styling, legend)
- `farmers_market` and `farmers_market_full` examples; home renovation test fixture
- 45+ tests passing

Canonical status: **`skills/schedule/context/prd.md`** § MVP status.

---

## Done (for context)

- JSON Schema + logic validation (fail-fast before compute)
- CPM compute (`compute_lib.py`) with critical path
- CLIs: `validate`, `compute` (writes `gantt_data.json`, deploys viewer, stdout + serve by default)
- Static Gantt viewer (`gantt.html`, `gantt.js`, `gantt_theme.css`) — bars, milestones, dependency lines, critical styling
- Task timing modes (R19–R23)
- Architecture docs, examples, evals
- Agent workflow in `SKILL.md` (don’t modify skill code; propose fixes before editing YAML)

---

## High priority — MVP gaps

All items **done**. See § Done and § MVP complete above.

### 1. Critical path

- **Status:** Done
- **What:** Identify and expose the longest dependent chain (determines project finish).
- **Where:** `compute_lib.py` + `gantt_data.json` / stdout JSON (`is_critical` on each item).

### 2. Gantt dependency lines

- **Status:** Done
- **What:** Draw predecessor links between bars (FS/SS/FF/SF-aware anchor points).
- **Where:** `assets/gantt.js` + `predecessors` on each item in JSON from `computed_schedule_to_dict()`.

### 3. Task timing modes (pinned task dates)

- **Status:** Done
- **Design:** `skills/schedule/context/task_timing_modes.md`

### 4. Tighten logic validation (predecessor listing rules)

- **Status:** Done
- Exact `["0FS"]` for top-level project anchor; exact `["{parentId}SS"]` when child lists only its parent
- Calendar required for logic validation when schedule has milestones (working-day, pinned-task, and milestone-reachability checks)

---

## Medium priority — docs & consistency

### 5. Sync PRD with validate-first architecture

- **Status:** Done — PRD restored with file-format requirements; R18 = hard errors; resolved decisions in `decisions.md`

### 6. Expand evals

- **Status:** Done — 9 eval cases in `skills/schedule/evals/evals.json`

### 7. `.gitignore` for generated Gantt artifacts

- **Status:** Done — `skills/schedule/.gitignore` + note in `SKILL.md`

---

## Lower priority — polish

### 8. Gantt hot reload (PRD R10)

- **Status:** Shelved — see `skills/schedule/context/live_refresh.md`
- **Why:** Manual refresh after re-running `compute` is enough for MVP; full loop (browser poll + `compute --watch`) is dev-only polish.
- **When to revisit:** Frequent local iterate-on-YAML + Gantt sessions become a common pain point.

### 9. Validate milestone working days without full calendar requirement

- **Status:** Resolved — logic validation requires calendar when schedule has milestones

### 10. Editor schema hints

- **Status:** Done
- Modelines on example and fixture schedule/calendar YAML; agent guidance in `SKILL.md`.

---

## Explicitly out of scope (MVP — do not implement unless scope changes)

From `skills/schedule/context/prd.md`:

- Interactive Gantt editing (drag bars, links)
- Fixed dates on groups (use milestone + predecessor)
- Hour-based durations
- Resource leveling, cost, baselines, actuals
- Cross-project predecessor links
- Custom work weeks / partial work days

---

## Suggested implementation order

All MVP steps complete or shelved:

1. ~~Critical path (JSON + agent reporting)~~
2. ~~Predecessors in JSON + Gantt dependency lines~~
3. ~~Task timing modes~~
4. ~~Stricter listing validation~~
5. ~~PRD sync (validate-first drift)~~
6. ~~Hot reload~~ — shelved (`live_refresh.md`)
7. ~~Evals + gitignore~~

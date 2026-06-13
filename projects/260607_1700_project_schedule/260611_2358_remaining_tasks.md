# Schedule Skill — Remaining Tasks

**Created:** 2026-06-11 23:58  
**Status:** Active backlog  
**Skill location:** `skills/schedule/`  
**Design docs:** `projects/260607_1700_project_schedule/`, `skills/schedule/references/`

## Done (for context)

- JSON Schema + logic validation (fail-fast before compute)
- CPM compute (`compute_lib.py`)
- CLIs: `validate`, `compute` (merged render; writes `gantt_data.json`, deploys viewer, stdout + serve by default)
- Static Gantt viewer (`assets/gantt.html`, `assets/gantt.js`) — bars, milestones, dependency lines, critical styling
- Architecture docs, landscaping example, critical path in compute output, 25+ tests passing
- Agent workflow in `SKILL.md` (don’t modify skill code; propose fixes before editing YAML)

---

## High priority — MVP gaps

### 1. Critical path

- **Status:** Done
- **What:** Identify and expose the longest dependent chain (determines project finish).
- **Where:** `compute_lib.py` + `gantt_data.json` / stdout JSON (`is_critical` on each item).
- **Notes:** Backward walk from terminal tasks; Gantt viewer styles critical bars in a distinct color.

### 2. Gantt dependency lines

- **Status:** Done
- **What:** Draw predecessor links between bars (FS/SS/FF/SF-aware anchor points).
- **Where:** `assets/gantt.js` + `predecessors` on each item in JSON from `computed_schedule_to_dict()`.

### 3. Task timing modes (pinned task dates)

- **Design:** `skills/schedule/references/task_timing_modes.md`
- **PRD:** R19–R23 in `references/prd.md` (Implement later)
- **What:** Required `timing` field on every task (`auto` | `start_duration` | `start_finish` | `finish_duration`). User pins two of start/finish/duration; engine computes the third. Predecessors stay required; fixed dates win; bound violations fail validation.
- **Scope:** Minor extension — schema + logic validation + `_schedule_task` branch. Groups unchanged (milestone + predecessor for phase gates).
- **Not doing:** fixed group dates, optional/default `timing`, backward compatibility for omitted `timing`
- **Steps:**
  1. Schema — required `timing`, conditional `start`/`finish`/`duration`
  2. Update all test fixtures and examples with explicit `timing: auto`
  3. Logic validation — predecessor bounds, parent floor, `start_finish` sanity
  4. Compute — pinned branches; do not overwrite pins in fixed-point loop
  5. Docs + SKILL.md + evals

### 4. Tighten logic validation (predecessor listing rules)

Partially enforced in `logic_validate_lib.py`. Still missing or weak:

| Rule | Status |
|------|--------|
| Top-level with no other preds → exactly `["0FS"]` | Not enforced (only “no 0FS mixed with others”) |
| Child with no other preds → exactly `["{parentId}SS"]` | Not enforced (only “child must not reference id 0”) |
| Milestone working days when calendar missing on `validate` | Skipped if calendar not loaded |

Add tests in `test_logic_validate_lib.py` for each new rule.

---

## Medium priority — docs & consistency

### 5. Sync PRD with validate-first architecture

- **File:** `skills/schedule/references/prd.md` (and optionally `projects/260607_1700_project_schedule/PRD.md`)
- **Drift:** R16/R18 still describe **warnings**; engine now **errors** at validation and has no warnings channel.
- **Drift:** Agent table still says “Interpret warnings, suggest fixes”.
- **Drift:** R9 mentions `schedule-render`; now `compute` deploys viewer.
- Update open questions / checklist as needed.

### 6. Expand evals

- **File:** `skills/schedule/evals/evals.json`
- Add cases for: validation error listing, cycle/duplicate ID fix, `compute` + Gantt workflow, critical path (once implemented).

### 7. `.gitignore` for generated Gantt artifacts

- Generated in project dirs: `gantt_data.json`, `gantt.html`, `gantt.js`
- Example run leaves untracked files under `examples/landscaping/`
- Consider `examples/**/gantt*.json` etc. or document “never commit generated output” in `SKILL.md` only.

---

## Lower priority — polish

### 8. Gantt hot reload (PRD R10)

- **What:** Page auto-updates when schedule/data changes during development.
- **Minimal approach:** Poll `gantt_data.json` every N seconds in `gantt.js`, re-render on change.
- **Full loop:** File watcher + re-run `compute` on `schedule.yaml` change (separate dev tool; optional).

### 9. Validate milestone working days without full calendar requirement

- `validate` allows missing calendar; milestone working-day checks skipped.
- Decide: require calendar for logic validation always, or document current behavior.

### 10. Push to remote

- Branch `main` is **6 commits ahead** of `origin/main` (as of 2026-06-11).

### 11. Editor schema hints

- Optional modeline or README note for Red Hat YAML + `schemas/*.schema.yaml` on example projects.

---

## Explicitly out of scope (MVP — do not implement unless scope changes)

From `references/prd.md`:

- Interactive Gantt editing (drag bars, links)
- Fixed dates on groups (use milestone + predecessor)
- Hour-based durations
- Resource leveling, cost, baselines, actuals
- Cross-project predecessor links
- Custom work weeks / partial work days

---

## Suggested implementation order

1. ~~Critical path (JSON + agent reporting)~~
2. ~~Predecessors in JSON + Gantt dependency lines~~
3. Task timing modes (R19–R23)
4. Stricter listing validation
5. PRD sync (validate-first drift)
6. Hot reload (optional polish)
7. Evals + gitignore + push

---

## File touch map (when implementing)

| Task | Likely files |
|------|----------------|
| Critical path | `compute_lib.py`, tests, `scheduling_algorithm.md`, `gantt_data.json` shape |
| Dependency lines | `compute_lib.py` (JSON), `assets/gantt.js`, `assets/gantt.html` |
| Listing validation | `logic_validate_lib.py`, `test_logic_validate_lib.py`, `data_model.md` |
| Task timing modes | `task_timing_modes.md`, schema, `logic_validate_lib.py`, `compute_lib.py`, tests, examples |
| PRD sync | `references/prd.md`, `projects/.../PRD.md` |
| Hot reload | `assets/gantt.js` |

# Scheduling Algorithm

High-level steps performed by `compute_schedule()` in `compute_lib.py`. **Validation runs first** — see `architecture.md`. Compute assumes clean input and never writes back to YAML files.

Implementation: `src/schedule/compute_lib.py`. Calendar math: `calendar_lib.py`. Predecessor parsing: `predecessors_lib.py`.

## Prerequisites

Before compute runs, `load_schedule_project()` (or equivalent) must pass:

1. **JSON Schema validation** — shape and field constraints
2. **Logic validation** — unique IDs, valid predecessor refs, acyclic graph, listing rules, milestones on working days

If validation fails, compute is not run. Fix the schedule file and re-validate.

## Inputs

- **Schedule data** — parsed YAML with nested `items` (milestones, tasks, groups)
- **Calendar data** — weekends and holidays for working-day arithmetic

## Steps

### 1. Build scheduling context

- Parse the working calendar from calendar data
- Flatten nested groups into a single item list (each item keeps its `parent_id`)
- Index items by ID
- Partition items into tasks, groups (deepest-first for rollup order), and milestones

### 2. Apply milestone dates

- For each milestone, copy the authoritative `date` to both `start` and `finish`

### 3. Fixed-point scheduling pass

Repeat until no item dates change (or iteration limit reached):

1. **Schedule tasks** — for each task with a duration:
   - Compute earliest start from all predecessor links (latest constraint wins)
   - Apply parent floor: children cannot start before their parent group's anchor start (R2)
   - Compute finish from start + duration using working-day calendar math
2. **Roll up groups** — for each group (deepest nested groups first):
   - Wait until all children have start/finish
   - Start = max(child start, predecessor-implied start)
   - Finish = latest child finish

Tasks and groups waiting on predecessor anchors that are not yet scheduled are skipped until a later iteration.

### 4. Project finish

- Latest `finish` date among all scheduled items

### 5. Critical path

- Walk backward from task(s) finishing on `project_finish` through **driving** predecessors:
  - Predecessor links where the computed constraint equals the item's actual start
  - For groups, children whose finish equals the group finish (rollup drivers)
- Set `is_critical: true` on each item in that chain (others default to `false`)
- Output per item in JSON / stdout — used by the Gantt viewer for bar styling

Driving-predecessor detection avoids full total-float math; it is enough to highlight the chain that sets project finish.

## Predecessor link semantics

For each link type, the engine computes the **earliest allowed start** for the successor:

| Link | Anchor from predecessor | Result |
|------|-------------------------|--------|
| FS | Predecessor finish | Start after finish (+ lag), normalized to working day |
| SS | Predecessor start | Start at same time (+ lag), normalized to working day |
| FF | Predecessor finish | Back-calculate start so finishes align (+ lag) |
| SF | Predecessor start | Back-calculate start from predecessor start (+ lag) |

Milestone predecessors expose the same date as both start and finish anchors.

Group predecessors expose only a start anchor until children roll up; FS and FF links wait until the group has a computed finish.

When an item has multiple predecessors, the **latest** required start date applies.

## Output

- Flat list of items with computed `start`, `finish`, and `is_critical`
- `project_finish` date

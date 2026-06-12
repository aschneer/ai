# Scheduling Algorithm

High-level steps performed by `compute_schedule()` in `compute_lib.py`. The engine is read-only: it validates input, computes dates, and emits warnings — it never writes back to YAML files.

Implementation: `src/schedule/compute_lib.py`. Calendar math: `calendar_lib.py`. Predecessor parsing: `predecessors_lib.py`.

## Inputs

- **Schedule data** — parsed YAML with nested `items` (milestones, tasks, groups)
- **Calendar data** — weekends and holidays for working-day arithmetic

## Steps

### 1. Build scheduling context

- Parse the working calendar from calendar data
- Flatten nested groups into a single item list (each item keeps its `parent_id`)
- Index items by ID; warn on duplicate IDs (last occurrence wins)
- Partition items into tasks, groups (deepest-first for rollup order), and milestones

### 2. Check predecessor references

- For every predecessor link on every item, warn if the referenced task ID does not exist

### 3. Apply milestone dates

- For each milestone, copy the authoritative `date` to both `start` and `finish`
- Warn when a milestone date falls on a non-working day (the date is **not** moved)
- Successors linked via FS/SS normalize their computed **start** to the next working day after the constraint

### 4. Fixed-point scheduling pass

Repeat until no item dates change (or iteration limit reached):

1. **Schedule tasks** — for each task with a duration:
   - Compute earliest start from all predecessor links (latest constraint wins)
   - Apply parent floor: children cannot start before their parent group's anchor start (R2)
   - Compute finish from start + duration using working-day calendar math
2. **Roll up groups** — for each group (deepest nested groups first):
   - Wait until all children have start/finish
   - Start = max(child start, predecessor-implied start)
   - Finish = latest child finish

Tasks and groups with missing predecessor anchors (e.g. cyclic dependencies, predecessor not yet scheduled) are skipped until a later iteration or left unscheduled.

### 5. Post-scheduling warnings

- **Unscheduled items** — tasks or groups that never received dates
- **Constraint not met** — computed start is earlier than a predecessor link requires
- **Milestone constraint** — task dates conflict with a linked milestone's authoritative date

### 6. Project finish

- Latest `finish` date among all scheduled items

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

- Flat list of items with computed `start` and `finish`
- `project_finish` date
- List of warnings (non-fatal logic problems)

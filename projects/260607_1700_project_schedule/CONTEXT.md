# Project Scheduling

A text-native alternative to Microsoft Project Auto Schedule — tasks, durations, and predecessor dependencies stored in a human-readable file, with dates computed automatically on a working calendar.

## Language

**Schedule**:
The complete project plan: tasks, their hierarchy, durations, dependencies, and computed dates.
_Avoid_: Plan file, project file, Gantt

**Schedule file**:
The durable structured data artifact (e.g. YAML) that is the source of truth for a schedule. Both the user and the agent read and edit this file directly. Validated against a JSON Schema before scheduling.
_Avoid_: Database, session state, UI state

**Kind**:
The required first field on every schedule item. Primary discriminator — all other fields are validated against it. Values: `milestone`, `task`, or group kind (name TBD, leading candidate: `group`).
_Avoid_: Type, category, class

**Milestone** (`kind: milestone`):
A zero-duration point in the schedule with a user-entered `date`. Cannot have predecessors or children. Can only be referenced as a predecessor by other items. The only way to place a user-defined date constraint.
_Avoid_: Checkpoint, marker, event

**Task** (`kind: task`):
A leaf work item with a `duration` and `predecessors` list. No `date`, no `children`. Timing is computed.
_Avoid_: Activity, item, row

**Group** (`kind: group`, name TBD):
A parent item that groups children. Has `predecessors` and `children` (minimum one child, schema-strict). No `date`, no `duration` — dates and duration span are derived from descendants. Microsoft Project calls this a summary task; we are choosing a different `kind` name.
_Avoid_: Summary, category, folder, epic

**Unique ID**:
A stable, permanent integer identifier for a schedule item. ID 0 is reserved for the project start milestone. IDs 1+ are assigned once at creation and never renumbered when items are reordered.
_Avoid_: Task ID, row number, line number, index, hash

**Project start milestone**:
The milestone at Unique ID 0. Anchors the entire project.
_Avoid_: Day zero, kickoff task

**Date**:
The single user-entered calendar date on a milestone. Authoritative — the scheduling engine does not override it. Forbidden on `task` and `summary` kinds.
_Avoid_: Start date, finish date, end date

**Milestone predecessor equivalence**:
When a predecessor link targets a milestone, all link types (FS, SS, FF, SF) resolve to the same date, because start and finish are identical on zero-duration items.
_Avoid_: Link type normalization

**Predecessor link**:
A directed scheduling constraint from one item to another, expressed as an MS Project format string (e.g. `14FS+3d`) in an inline predecessors list.
_Avoid_: Dependency, edge, blocker

**Predecessors**:
An inline list of immediate predecessor link strings. Allowed only on `task` and group kinds — never on milestones. Either `0FS` alone, or other links without `0FS`. A child with no other predecessors lists its parent as `{parentId}SS`.
_Avoid_: Dependencies, links, all upstream tasks

**Local project start**:
The role a parent group plays for its children — no child may start before the group's effective start, analogous to how task 0 anchors the whole project.
_Avoid_: Sub-project start, phase gate

**Auto Schedule**:
The mode where start and finish dates are computed from durations, predecessors, milestone date anchors, and the working calendar — the user does not manually set dates on tasks or summaries.
_Avoid_: Automatic scheduling, calculated schedule

**Working calendar**:
The real calendar used for scheduling. Weekends and configured holidays are non-working days; durations and lag count working days only.
_Avoid_: Business calendar, project calendar

**Scheduling engine**:
Deterministic code (not the LLM) that validates the schedule file, performs critical-path scheduling, and produces computed dates for display.
_Avoid_: Agent, calculator, solver

**Skill**:
The agent playbook for working on schedule files — how to edit items, run the scheduling engine, interpret results, and regenerate visuals.
_Avoid_: App, tool, plugin

**Task order**:
The sequence items appear in the schedule file. A parent group appears immediately above its children; siblings at the same level are sorted by computed start date; top-level groups sorted by earliest child start.
_Avoid_: WBS order, sort order, row order

**Duration**:
Working time to complete a task, expressed in MS Project style notation (`4d`, `2w`, `8h`). Required on `task` kind only. Counts working days on the calendar.
_Avoid_: Effort, length, elapsed time

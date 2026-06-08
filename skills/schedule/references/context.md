# Project Scheduling

A text-native alternative to Microsoft Project Auto Schedule — delivered as an AI agent skill with modular library code for deterministic schedule calculation.

## Language

**Schedule**:
The complete project plan: tasks, their hierarchy, durations, dependencies, and computed dates.
_Avoid_: Plan file, project file, Gantt

**Project directory**:
A folder containing everything for one schedule: the schedule file (any name), calendar file, and generated artifacts such as Gantt HTML.
_Avoid_: Project folder, workspace

**Schedule file**:
The durable structured data artifact (YAML) that is the source of truth for a schedule. Filename is not prescribed. Edited only by the user and agent — never by scheduling code. References a calendar file by relative path. Validated against a JSON Schema file written in YAML.
_Avoid_: Database, session state, UI state

**JSON Schema**:
The validation standard for schedule and calendar files. Schema files use JSON Schema semantics (`type`, `required`, `oneOf`, `properties`, etc.) but are **authored in YAML** (e.g. `schedule.schema.yaml`). YAML data files are validated against these schemas — in the editor via Red Hat YAML, and at runtime via library code.
_Avoid_: YAML Schema, Kwalify, custom schema format

**Calendar file**:
A separate YAML file in the project directory listing non-working days (holidays) and weekend configuration. Referenced by path from the schedule file.
_Avoid_: Holiday list, calendar config, inline holidays

**Kind**:
The required first field on every schedule item. Primary discriminator — all other fields are validated against it. Values: `milestone`, `task`, or `group`.
_Avoid_: Type, category, class

**Milestone** (`kind: milestone`):
A zero-duration point in the schedule with a user-entered `date`. Cannot have predecessors or children. Can only be referenced as a predecessor by other items. The only way to place a user-defined date constraint.
_Avoid_: Checkpoint, marker, event

**Task** (`kind: task`):
A leaf work item with a `duration` and `predecessors` list. No `date`, no `children`. Timing is computed.
_Avoid_: Activity, item, row

**Group** (`kind: group`):
A parent item that groups children. Has `predecessors` and `children` (minimum one child, schema-strict). No `date`, no `duration` — dates and duration span are derived from descendants. Microsoft Project equivalent: summary task.
_Avoid_: Summary, category, folder, epic

**Unique ID**:
A stable, permanent integer identifier for a schedule item. ID 0 is reserved for the project start milestone. IDs 1+ are assigned once at creation and never renumbered when items are reordered.
_Avoid_: Task ID, row number, line number, index, hash

**Project start milestone**:
The milestone at Unique ID 0. Anchors the entire project.
_Avoid_: Day zero, kickoff task

**Date**:
The single user-entered calendar date on a milestone. Authoritative — the scheduling engine does not override it. Forbidden on `task` and `group` kinds.
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
The mode where start and finish dates are computed from durations, predecessors, milestone date anchors, and the working calendar — the user does not manually set dates on tasks or groups.
_Avoid_: Automatic scheduling, calculated schedule

**CPM (Critical Path Method)**:
The deterministic algorithm that calculates task dates from durations, predecessor dependencies, and calendar constraints. Identifies the longest dependent chain (critical path) that determines project finish. Always implemented in library code, never by the agent.
_Avoid_: Critical path analysis, scheduling algorithm

**Working calendar**:
The real calendar used for scheduling, defined in a calendar file. Weekends and configured holidays are non-working days; durations and lag count working days only.
_Avoid_: Business calendar, project calendar

**Scheduling engine**:
Deterministic library code that validates schedule files, performs CPM scheduling, and produces computed output. Read-only — never modifies source files.
_Avoid_: Agent, calculator, solver

**Skill**:
The Schedule AI agent skill (`skills/schedule/SKILL.md`) — playbook for working on schedule files, composing library modules, interpreting results, and regenerating the Gantt. The agent edits files; libraries calculate.
_Avoid_: App, tool, plugin

**Task order**:
The sequence items appear in the schedule file, controlled by the user and agent — never rewritten by scheduling code. Recommended convention: parent group immediately above its children; siblings sorted by computed start date; top-level groups sorted by earliest child start.
_Avoid_: WBS order, sort order, row order

**Duration**:
Working time to complete a task, expressed as days or weeks (`4d`, `2w`). Required on `task` kind only. Counts working days on the calendar.
_Avoid_: Effort, length, elapsed time, hours

# Project Schedule — Product Requirements Document

**Status:** MVP complete
**Last updated:** 2026-07-20

## Overview

A text-native alternative to Microsoft Project **Auto Schedule**: a project schedule lives in human-readable YAML that a user and an AI agent edit, a deterministic engine computes dates from durations and dependencies, and the user views the result as a Gantt chart and reports. The deliverable is an **AI agent skill** (`SKILL.md` + validation schemas + scheduling libraries), not a standalone application. It targets users managing renovation, landscaping, construction, or similar projects who want schedules in git with Microsoft Project scheduling semantics.

The concrete file shape, field-by-field rules, and examples are defined canonically in **`data_model.md`**; engineering choices (modules, CLIs, algorithms) are in **`architecture.md`**. This document states **what the product must do**, from the customer's perspective. Every requirement is addressed by its `N.M` number.

## Requirements

- 1. Schedule structure
    - 1.1. A user builds a schedule from exactly three kinds of items: **milestones** (fixed points in time), **tasks** (work that takes time), and **groups** (containers that organize and roll up other items).
        - 1.1.1. Every item declares which kind it is, as its first field.
        - 1.1.2. Every item has a human-readable name.
    - 1.2. Every schedule has a single project-start point that anchors all other work; all other work is ultimately constrained from this date.
        - 1.2.1. The project start is a milestone with the reserved identifier `0`, never reassigned.
        - 1.2.2. The user sets the project-start date.
    - 1.3. Groups can contain tasks, milestones, and other groups to arbitrary nesting depth, so a user can organize a project into phases and sub-phases.
    - 1.4. Hierarchy is visible in the schedule file through indentation.

- 2. Authored vs. computed dates
    - 2.1. A user gives a duration only to a task (the work it represents); a group and a milestone carry no user-entered duration.
        - 2.1.1. A group's duration and dates are derived from its children, never entered by hand.
        - 2.1.2. A milestone's duration is zero (implicit — no duration field).
    - 2.2. For ordinary planning, the user never types start/finish dates onto tasks or groups; the tool computes them. (Committed task dates are available through timing modes — §5.)
    - 2.3. In the schedule file, only milestones carry a date field. All other timing is computed at render time, not stored in source YAML.
    - 2.4. A group's duration and dates roll up from its children:
        - 2.4.1. Duration is the span from earliest child start to latest child finish (not a sum of child durations).
        - 2.4.2. Start is the earliest child start, but no earlier than the group's own predecessor constraints (§3.6).
        - 2.4.3. Finish is the latest child finish.

- 3. Dependencies
    - 3.1. A user expresses dependencies with the four standard Microsoft Project link types (finish-to-start, start-to-start, finish-to-finish, start-to-finish) and optional lead/lag time, so behavior matches what MS Project users expect.
    - 3.2. A user lists only **immediate** predecessors for each item. The concrete string format and listing rules are defined in `data_model.md`.
    - 3.3. Tasks and groups depend on other items, and the dependency **moves** them.
    - 3.4. A predecessor is required only for a duration-only (`auto`) task, which needs a dependency to anchor its dates; self-anchoring items — pinned tasks (§5) and groups — may omit predecessors.
    - 3.5. An item with no predecessors shows no dependency arrow in the Gantt, so the schedule can hold items that simply occupy calendar space (e.g. team availability) without visual clutter.
    - 3.6. When a group has predecessors, none of its children can start before the group does — a group behaves as a "local project start" for its subtree.
    - 3.7. When a predecessor link targets a milestone, all link types resolve to that milestone's single date.
    - 3.8. A milestone's date is always authoritative; a predecessor never moves it.
        - 3.8.1. A milestone may carry a single **finish-to-start, no-lag** predecessor as a deadline annotation only — declaring that a chain of work culminates in that fixed date. Any other link type or a lag is rejected, having no schedulable meaning against a fixed point.
        - 3.8.2. The annotated link is drawn in the Gantt.
        - 3.8.3. If the annotated chain finishes after the milestone date, the deadline is unreachable and validation fails (§6.7).
        - 3.8.4. A plain deadline milestone does not place its chain on the critical path; only a designated project-finish milestone does (§3.9).
    - 3.9. At most one milestone per schedule may be designated the project finish (`type: project_finish`), and it must list a predecessor chain (the culminating work).
        - 3.9.1. Its date is the project **deadline**.
        - 3.9.2. The reported **project finish** is when the feeding chain actually completes, which may be earlier than the deadline (buffer) — matching Microsoft Project, where finish is when work ends and the deadline is shown separately.
        - 3.9.3. The **critical path** is the zero-slack chain feeding the milestone: critical when the feeding work finishes exactly on the date, empty when the work finishes early.
        - 3.9.4. With no designated project-finish milestone, project finish is the latest computed finish among all items and the critical path is the longest path to it.

- 4. Milestones
    - 4.1. A milestone is the way a user places a fixed point in time that other items can depend on (e.g. a permit-approved date downstream work keys off).
    - 4.2. A milestone is the only mechanism for a user-defined date constraint at a point in the schedule; other items reference that point via predecessor links.
    - 4.3. A milestone has a stable identifier and a user-entered, authoritative date the engine never overrides.
    - 4.4. A milestone's date must fall on a working day in the calendar; otherwise validation fails with an error.

- 5. Committed (pinned) task timing
    - 5.1. Every task must declare a `timing` mode explicitly — never optional, never inferred. The mode names and the fields each requires are defined in `data_model.md`.
    - 5.2. Beyond plain auto-scheduling, a user can commit a task to a specific start, a specific finish, or a fixed start-and-finish window, and the engine computes the remaining field, supporting execution workflows ("the crew starts Monday") without abandoning dependency checking.
    - 5.3. Predecessors remain required in all timing modes; pinned start/finish values are authoritative, and predecessors define the earliest allowable bounds.
    - 5.4. A committed date that conflicts with the task's dependencies is reported as an error for the user to resolve; the tool never silently moves a date the user pinned (§6.7).

- 6. Scheduling engine
    - 6.1. All date calculation is deterministic library code, never LLM inference. An agent edits and interprets schedule files; it never performs date math.
    - 6.2. The engine automatically calculates start and finish dates from task durations, predecessor relationships (link type and lag/lead), the project-start milestone, parent-group predecessor constraints on children (§3.6), and the working calendar.
    - 6.3. Durations and lag/lead use Microsoft Project suffix notation, days and weeks only (no hours). A `4d` duration means four working days. Exact notation: `data_model.md`.
    - 6.4. The working calendar defines working days:
        - 6.4.1. No work on Saturday or Sunday.
        - 6.4.2. No work on configured holidays.
        - 6.4.3. Schedule dates are calendar dates; durations are working-day durations, and start/finish calculations skip non-working days when counting duration and applying lag/lead.
        - 6.4.4. The calendar lives in a separate file referenced from the schedule; its path is relative to the schedule file (shape in `data_model.md`).
    - 6.5. The engine validates both schedule and calendar files against the shipped JSON Schemas (`schemas/schedule.schema.yaml`, `schemas/calendar.schema.yaml`) **before** computing; files that violate the format are rejected with clear errors, and the user or agent fixes the file and retries.
    - 6.6. The engine is read-only over source data: on each run it validates, computes, and writes only separate generated output (JSON, Gantt artifacts, reports). It never modifies the user's schedule or calendar files; only the user and agent edit source data.
    - 6.7. Impossible schedules are hard errors, not warnings, and the engine never auto-fixes or silently adjusts user data. Examples: cyclic predecessor dependencies; unknown predecessor IDs; a computed or pinned schedule that cannot satisfy a milestone date; duplicate IDs; invalid predecessor listing; a milestone on a non-working day.
    - 6.8. The engine identifies the items on the critical path (§3.9), and the user sees critical items in the Gantt and in computed output for reports and agent summaries.

- 7. Identity and ordering
    - 7.1. Each item has a permanent integer identifier that behaves like a Microsoft Project **Unique ID**.
        - 7.1.1. IDs 1 and up are assigned once at creation (next available integer); ID 0 is reserved for the project-start milestone (§1.2.1).
        - 7.1.2. IDs are never automatically renumbered when items are reordered, and predecessor references remain valid after reordering.
        - 7.1.3. IDs are opaque references, not list position; gaps in the sequence after deletion are acceptable.
    - 7.2. The order of items in the schedule is controlled by the user and agent and drives the order rows appear in the Gantt; the tool never reorders the user's file (recommended ordering convention: `data_model.md`).
    - 7.3. The schedule file is the source of truth — not chat history, not a proprietary database — stored as indented YAML a user and agent can read and edit directly and that version-controls cleanly (git diffs).

- 8. People and events context
    - 8.1. A user can record two kinds of decorative context alongside the schedule: **people** (personnel availability — out of office, traveling, on vacation, work location; one band per person) and **events** (calendar context not tied to a person — company events, holidays of note, external dates).
    - 8.2. Both use labeled date-range segments; segments within a band do not overlap and may fall on any calendar day.
    - 8.3. People and events carry no identifiers or dependencies and never affect task scheduling, the critical path, or project finish.

- 9. Gantt chart
    - 9.1. The schedule is viewable as a Gantt chart showing task and group bars, milestones, dependency links (FS/SS/FF/SF), and critical-path highlighting.
        - 9.1.1. Items with no predecessors show no dependency arrow (§3.5).
        - 9.1.2. The Gantt is regenerated when the user or agent runs a compute step.
        - 9.1.3. Interactive drag-and-drop editing is not required.
    - 9.2. After compute, the user can open the Gantt in a browser:
        - 9.2.1. On the same machine or remotely (SSH with port forwarding or network URL).
        - 9.2.2. The tool prints URLs; the user opens manually — no auto-open browser.
        - 9.2.3. The chart must be reachable on the network when working on a remote server (LAN, Tailscale, etc.).
    - 9.3. In the viewer, the user can collapse and expand nested groups to control how much hierarchy is shown.
        - 9.3.1. Collapsing a group hides its descendant rows while keeping the group's own summary bar and any dependency links to or from the group.
        - 9.3.2. Collapse and expand work at arbitrary nesting depth, independently per group.
        - 9.3.3. A single control collapses or expands all groups at once.
        - 9.3.4. This is a view-only control — it never changes the schedule file, computed dates, or row order.
    - 9.4. The user can print the schedule — to a printer, PDF, or other static document — for viewing and sharing. The output must be clean and faithful to the on-screen Gantt: task and group names, bars, milestones, dependency links, critical-path highlighting, and timeline alignment. The implementation (browser print, server-generated PDF, etc.) is not prescribed.
    - 9.5. Each schedule row is one line tall: the item name and its date range share a single line (name truncates first when space is tight; the full name is available on hover), and dates use a compact `mm/dd/yy` form, keeping the maximum number of rows visible without hiding information.
    - 9.6. The current year must be readable in the date-scale header from any horizontal scroll position — the year label stays visible as the user scrolls within a year and updates at each year boundary. (Month and day are inherently visible per column.)
    - 9.7. While the cursor is over the plot area (the bars, not the label column), the Gantt shows a subtle vertical line following the cursor, so the user can line a bar up with the date header. The line spans the visible plot height and disappears when the cursor is over the label column or leaves the plot.
    - 9.8. When today falls within the schedule's date range, the Gantt marks it with a distinct vertical line labeled "Today" spanning the plot height.
        - 9.8.1. The current date is determined at view time, not at compute — the line reflects the real date whenever the chart is opened.
        - 9.8.2. When today falls outside the range, no indicator is shown and the date axis is not extended to reach it — a schedule opened long after it ended stays at its own width.
        - 9.8.3. The today line draws on top of every row, including a locked people/events band, and is never occluded by content.
        - 9.8.4. The line is confined to the timeline area and never draws over the left-hand label column; when today's column scrolls behind the label column, the line is clipped away and disappears once fully behind it.
        - 9.8.5. The line stays below the sticky date-scale header/annotation lane and does not cross the date scale.
        - 9.8.6. The "Today" label sits in the annotation lane (§9.10), pinned under the date header, so it stays visible on vertical scroll.
    - 9.9. When a schedule declares people and/or events context (§8), the Gantt shows them as bands above the schedule rows.
        - 9.9.1. People rows on top, events rows below; each is a row with labeled segments on the same timeline.
        - 9.9.2. Two distinct colors (shown in the legend) and truncated labels; segments show a hover tooltip (§9.11).
        - 9.9.3. The date axis extends to include context segments that fall outside the task range.
        - 9.9.4. The bands are decorative — they never change computed dates, the critical path, or project finish.
    - 9.10. The people/events band has two viewer controls, both hosted in a thin annotation lane pinned directly under the date-scale header so they remain visible while scrolling.
        - 9.10.1. **Collapse** — a toggle that hides all people and events rows, leaving only the lane; expanding restores them. Default expanded.
        - 9.10.2. **Lock** — a toggle that pins the whole band (people rows, then events rows) directly below the header while the schedule scrolls vertically; one lock covers both bands. When the band is collapsed, the lock control is not shown.
        - 9.10.3. The lane displays a distinct "Context" section label so the band reads as chrome, not a schedule item.
    - 9.11. Hovering any bar, milestone, or context segment in the Gantt shows a tooltip.
        - 9.11.1. A task or group bar shows: item name; working-day count (e.g. `5 working days`); calendar-day count (e.g. `7 calendar days`).
        - 9.11.2. A milestone shows: milestone name; date.
        - 9.11.3. A people/events segment shows: band name (left-pane label); segment label (text on the bar); date range.
        - 9.11.4. Dates use `mm/dd/yyyy`; a date range is `mm/dd/yyyy-mm/dd/yyyy`.
        - 9.11.5. Task and group tooltips show both the working-day and calendar-day count (they differ when a bar spans weekends or holidays); working days exclude non-working days per the calendar.
        - 9.11.6. Day counts are computed by the engine and carried in the computed output, not derived in the viewer.

- 10. Project directory
    - 10.1. Each schedule project lives in one directory containing the schedule file, the calendar file, and a `site/` subfolder for generated viewer artifacts.
    - 10.2. The skill asks the user for the schedule file path or project directory; the schedule filename is not prescribed.
    - 10.3. Generated viewer artifacts are written into `site/` under the project directory, not beside the YAML source files.

## Deferred — Implement Later

- D1. **Live refresh.** While developing a schedule, the Gantt updates when the schedule file changes without manual refresh. Shelved; implementation plan and rationale in `live_refresh.md`.

## Out of scope

The following are deliberately excluded:

- Interactive Gantt editing (drag bars, drag links)
- Hour-based durations and lag (`8h`)
- Engine rewriting schedule file order or content
- Cross-project predecessor links
- Resource assignment / leveling
- Cost tracking
- Partial work days / custom work weeks (e.g. four-day week)
- Baselines / actuals / % complete

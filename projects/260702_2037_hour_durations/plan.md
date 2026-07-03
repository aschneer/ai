# Hour Durations — Implementation Plan

Ordered task list. Design rules live in the schedule skill docs
(`skills/schedule/context/{prd,data_model}.md`, `SKILL.md`) and are updated as
part of this work. This doc tracks order and status only.

Status: `[ ]` todo · `[~]` in progress · `[x]` done

## Goal

Let `auto` tasks take **sub-day durations in hours** (`1h`, `4h`) so a project can
capture many short tasks without rounding each up to a full day. Hour tasks pack
into a working day up to a calendar-defined capacity, then spill to the next
working day. A group of short tasks rolls up to a realistic calendar span.

## Model (locked in discussion)

Concise summary; full reasoning and trade-offs in **`decisions.md`** (this folder).

- **`hours_per_day`** — **required** new field in `calendar.yaml`. Day capacity.
- **Duration grammar** — add `h` (`1h`, `4h`) alongside `d`, `w`.
  - `h` valid **only on `auto` tasks**. `h` on a pinned task → validation error.
  - Reject `h >= hours_per_day` (tell the agent to use `d`/`w`). Hours are strictly sub-day.
- **Lag** — allow `h` (`+2h`) in predecessor lag.
- **Internal position** — `(date, minutes_into_day)` integer pair. No wall-clock,
  no time-of-day semantics — just elapsed working-minutes into the day.
- **Output** — **date-only**. A task's displayed `start`/`finish` are dates; its
  duration echoes the user's `Nh`. No fractional-day strings ever surface.
- **Packing** — hour tasks fill a day up to `hours_per_day`, then spill to the next
  working day. **No splitting**: a task that will not fit the remaining day starts
  fresh next working day at 0 minutes (an idle end-of-day gap is allowed).
- **Day tasks** — always day-aligned; next-working-day FS rule unchanged. A day-task
  successor of an hour task rounds to the next working day (ignores intraday finish).
  An hour task after a day task starts the next day at 0 minutes.
- **Milestones and pinned tasks** — date-only, unchanged.
- **Group rollup** — calendar span (earliest child start date → latest child finish
  date), unchanged rule. Now reflects hour-task packing.
- **Viewer** — day columns unchanged. Hour bars render as a fraction of the day
  column with an intraday start offset when packed mid-day.
- **Critical path / project finish** — compare the full `(date, minutes)` position
  internally; output the floored date. Hour tasks participate normally. Lone-critical
  and finish-date semantics as today (user reads their real terminal task).

## Phase 1 — Duration + calendar grammar
- [ ] `predecessors_lib.py`: extend `DURATION_PATTERN` to accept `h`; add a parser
      returning **working minutes** (or a `(unit, amount)` result). Keep the
      day-returning path for existing callers or migrate them (Phase 2).
- [ ] `calendar.schema.yaml`: add required `hours_per_day` (positive integer).
- [ ] `schedule.schema.yaml`: allow `h` in the duration pattern; constrain `h` to
      `auto` tasks (pinned modes reject `h`); allow `h` in lag pattern.
- [ ] Reject `h >= hours_per_day` — logic validation (needs calendar), with a clear
      message pointing the agent to use `d`/`w`.

## Phase 2 — Calendar + compute math
- [ ] `calendar_lib.py`: carry `hours_per_day`; add working-minute arithmetic —
      advance a `(date, minutes)` cursor by a duration, spilling across working days,
      no splitting.
- [ ] `compute_lib.py`: represent task start/finish internally as `(date, minutes)`;
      auto-task scheduler packs hour tasks against predecessor/parent position;
      day tasks stay day-aligned; FS/SS/FF/SF anchors respect the packing rules.
- [ ] Group rollup uses date parts (span) — confirm unchanged.
- [ ] Project finish + critical path compare full position, output floored date.
- [ ] Serialize output as date-only; echo `Nh` duration for hour tasks.

## Phase 3 — Tests
- [ ] Duration parser: `h` parses; `h >= hours_per_day` rejected; `h` on pinned task rejected.
- [ ] Packing: two 3h tasks FS in an 8h day → same day; third spills to next day.
- [ ] No-split: 5h task after a 5h task (8h day) → starts next day at 0min (gap on day 1).
- [ ] Parallel hour tasks (no deps) → all same day; group span = 1 day.
- [ ] Chained hour tasks exceeding a day → group span = correct multi-day.
- [ ] Day task successor of hour task → next working day (intraday finish ignored).
- [ ] Hour lag (`+2h`) shifts within/day and spills correctly.
- [ ] `hours_per_day` required — missing → validation error.
- [ ] Existing suite still passes.

## Phase 4 — Viewer
- [ ] `gantt.js`: bar geometry from `(date, minutes)` — fractional width + intraday
      start offset within the day column. Day/milestone rendering unchanged.
- [ ] Confirm links/critical highlighting still align with fractional bars.
- [ ] `gantt_data.json` payload carries whatever the viewer needs (minutes or
      fraction) without breaking the date-only display contract.

## Phase 5 — Docs
- [ ] `data_model.md`: duration grammar (`h`), `hours_per_day` calendar field, hour
      rules (auto-only, sub-day, packing, no split), group rollup note.
- [ ] `prd.md`: new DM/requirement for sub-day effort tracking; calendar `hours_per_day`.
- [ ] `SKILL.md`: authoring guidance — when/how to use hour tasks, restrictions.
- [ ] `README.md`: `hours_per_day` in calendar setup if it documents calendar shape.

## Phase 6 — Example + manual check
- [ ] Add `hours_per_day` to example calendars.
- [ ] Add a group of hour tasks (parallel + chained) to `farmers_market_full`.
- [ ] `uv run compute` clean; confirm packing, group span, fractional bars in the viewer.

## Phase 7 — Review
- [ ] Update project folder each phase; stop before each commit for user review.

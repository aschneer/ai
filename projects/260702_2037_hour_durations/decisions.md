# Hour Durations — Design Decisions

Most recent first. All entries below were settled together in the scoping
interview for this feature.

---

## 2026-07-03 05:19:00 UTC — Fixed hours-per-day, no wall-clock (fractional model)

**What:** Sub-day durations use a fixed `hours_per_day` capacity, not a real
time-of-day clock. There are no start/end times, lunch breaks, or 09:00 semantics.
A day is a bucket of `hours_per_day` working hours.

**Why:** The goal is to *bucket* many short tasks and estimate total project time,
not to schedule intraday. A real wall-clock engine (working-hour windows, datetimes
everywhere, intraday viewer grid) is weeks of work for capability the user does not
want. Fixed capacity gets the estimate right with a fraction of the cost.

**Trade-offs:** Cannot express "this task runs 2pm–4pm." Acceptable — explicitly out
of scope. Tasks only know *how long*, not *when* within a day.

---

## 2026-07-03 05:19:00 UTC — Internal position is (date, minutes_into_day) integer; output is date-only

**What:** The engine tracks each task's start/finish as an integer
`(date, minutes_into_day)` pair — elapsed working-minutes into the day, no clock.
All serialized output (`start`, `finish`, `project_finish`) is floored to a **date**.
A task's duration echoes the user's `Nh` string; no fractional-day strings ever surface.

**Why:** Considered a bare fractional-day float (`date + 0.375`). Rejected: floats drift
(1h/6h = 0.1666…, repeated adds land at 0.9999), and a lone float still cannot express
weekend/holiday skips — you need the date part separately regardless. Integer minutes
paired with the date are exact, spill cleanly across working days, and keep weekend skip
logic in the date component. This is the "internal time field, never displayed" idea done
as elapsed working-minutes rather than wall-clock.

**Trade-offs:** start/finish carry a hidden minutes component; finish and critical-path
comparisons must use the full pair, not the floored date, or a mid-day task mis-orders.
Noted in the plan.

---

## 2026-07-03 05:19:00 UTC — Hours only on auto tasks; pinned tasks and milestones stay date-only

**What:** The `h` unit is valid **only** on `auto`-timed tasks. Pinned tasks
(`start_duration`, `start_finish`, `finish_duration`) and milestones remain date-only.
`h` on a pinned task is a validation error.

**Why:** Hours exist to capture *effort* of short work the engine places automatically.
Pinned tasks and milestones are user-committed calendar anchors — intraday precision there
would reintroduce the wall-clock the whole design avoids, with no use case.

**Trade-offs:** Cannot pin a task to "start at 2h into day 3." Not wanted — pins are
date-level by design.

---

## 2026-07-03 05:19:00 UTC — Hours strictly sub-day; reject h >= hours_per_day

**What:** An hour duration must be smaller than a full day. `h >= hours_per_day` is a
validation error telling the agent to use `d`/`w` instead.

**Why:** Keeps `h` unambiguously "sub-day effort." A multi-day thing expressed in hours
would force task-splitting logic and blur the day/hour boundary. Days already model
day-or-longer work.

**Trade-offs:** `10h` with an 8h day is rejected; author writes `1d`+`2h` conceptually,
or rounds. Simplicity over completeness for v1.

---

## 2026-07-03 05:19:00 UTC — Hour tasks pack into a day, spill on overflow, no splitting

**What:** Hour tasks fill a working day up to `hours_per_day`, then spill to the next
working day. A task that will not fit the remaining hours of a day starts fresh at the
**next working day, 0 minutes** — it is never split across a day boundary. An idle
end-of-day gap is allowed.

**Why:** Packing is the whole point — N one-hour tasks should consume ~N/`hours_per_day`
days, not N days. No-splitting keeps each task a single contiguous bar and avoids
multi-segment rendering and fragmented compute. The occasional idle gap is a small price
for simple bars and simple math.

**Trade-offs:** A day may leave a few unused hours when the next task does not fit. Real
throughput is slightly under-packed; acceptable and easy to reason about.

---

## 2026-07-03 05:19:00 UTC — Day tasks stay day-aligned; hour↔day transitions round to day

**What:** Day-duration tasks remain day-aligned with the existing next-working-day FS rule.
A day-task successor of an hour task ignores the predecessor's intraday finish and starts
the next working day. An hour task following a day task starts the next day at 0 minutes.

**Why:** Preserves current day-task behavior exactly — no regression for existing schedules.
Only hour tasks introduce intraday position; anything day-grained snaps to day boundaries as
before.

**Trade-offs:** A day task after an hour task that finishes early in a day still waits until
the next day — mild pessimism, but matches the "day tasks are day-aligned" mental model.

---

## 2026-07-03 05:19:00 UTC — Group rollup stays calendar span (unchanged rule)

**What:** A group's dates remain earliest child start → latest child finish (calendar span),
not a sum of child effort hours. The rule is unchanged; it now simply reflects hour-task
packing.

**Why:** Span already answers "when does this bucket run and how long on the calendar." With
packing, 20 one-hour tasks chained land across ~2.5 days and the span shows ~2.5 days
automatically. An effort-sum semantic would be a second, conflicting meaning of "group total."

**Trade-offs:** Parallel hour tasks (no deps) all land on one day, so the group span reads
1 day even though total effort exceeds a day — correct, since they *can* all happen that day.
Effort total is not surfaced; span is.

---

## 2026-07-03 05:19:00 UTC — hours_per_day required in calendar.yaml; lag may use hours

**What:** `hours_per_day` is a **required** field in `calendar.yaml`. Predecessor lag may use
the `h` unit (`+2h`) in addition to `d`/`w`.

**Why:** Required (not defaulted) because hour semantics are meaningless without a stated
capacity, and an AI agent can update existing calendars to the new schema trivially — no need
to protect old files with a silent default. Hour lag falls out for free once the parser
handles `h` and keeps lag consistent with durations.

**Trade-offs:** Existing calendars fail validation until `hours_per_day` is added. Deliberate —
a one-line, agent-automatable migration, and better than a wrong implicit default.

---

## 2026-07-03 05:19:00 UTC — Viewer keeps day columns; hour tasks render as fractional bars

**What:** The Gantt keeps one column per calendar day. Hour tasks render as a fraction of a
day column (width = hours/`hours_per_day`) with an intraday start offset when packed mid-day.
Day and milestone rendering is unchanged.

**Why:** The day column is the timeline's fixed unit and the user wants it kept. Fractional
positioning within a cell shows short tasks without an intraday grid. Small bars are
acceptable for v1.

**Trade-offs:** Very short tasks (1h in an 8h day) render as a thin bar — visible but small.
Fine for now; no sub-day gridlines.

# Coverage Bars — Design Decisions

Most recent first. All entries below were settled together in the scoping
interview for this feature.

---

## 2026-07-03 05:42:00 UTC — Coverage is a new primitive, not reuse of group/tasks

**What:** Coverage is a dedicated concept: one horizontal band per person, split into
labeled date-range segments laid end-to-end on a single line. It is not modeled as a
group of pinned tasks.

**Why:** Tasks/groups/milestones are one-item-per-row with dependency and CPM semantics.
Coverage is one-row-many-segments with zero dependency semantics. Reusing a group would
stack segments vertically (the opposite of the goal) and still need the same viewer work to
lay them horizontally — all of the new-primitive cost plus contorting an existing type.

**Trade-offs:** A new concept to document and render. Worth it — it opts out of the
dependency/CPM machinery cleanly, the way a milestone opts out of duration.

---

## 2026-07-03 05:42:00 UTC — Root-level `coverage:` key, not inside `items`

**What:** Coverage lives at the root of the schedule file as its own `coverage:` array,
sibling to `items:` and `calendar:`. It is not an item `kind`.

```yaml
coverage:
  - name: Maria
    segments:
      - {start: 2026-05-11, finish: 2026-05-15, label: Out of office}
```

**Why:** `items` carries CPM semantics — IDs referenced by predecessors, row order as
timeline sort, rollup, cycle checks. Coverage has none. Inside `items`, every consumer
(listing rules, compute flatten, cycle check, ID resolution) would need a "skip if coverage"
special case — leaky. A separate root key keeps compute out of it entirely, lets the schema
validate it independently, and dissolves the row-order question (coverage is its own section
by construction).

**Trade-offs:** One more top-level key. Optional, so schedules without it are unaffected.

---

## 2026-07-03 05:42:00 UTC — Pure annotation; never affects the schedule

**What:** Coverage is decorative only. It never constrains task scheduling, never feeds the
critical path, and never changes `project_finish`. It is not resource leveling.

**Why:** The user wants availability graphed *alongside* the Gantt, not fed into it.
Resource-constrained scheduling is explicitly out of the PRD's scope. Keeping coverage inert
makes it a cheap pass-through with no compute logic.

**Trade-offs:** "Maria out of office" does not stop her tasks from being scheduled then — the
author manages that manually. Accepted; coverage is information, not a constraint.

---

## 2026-07-03 05:42:00 UTC — No IDs, no overlap, calendar days, required labels

**What:** Per the interview:
- **No IDs** on coverage entries or segments (nothing references them). Can add later.
- **No overlapping segments** within one person — a **hard validation error**.
- Segments use **calendar days**, not working days (vacations span weekends); `finish` is
  inclusive.
- **Label required** on every segment.

**Why:** Coverage has no dependency references, so IDs earn nothing yet. Non-overlap keeps
each person a single flat line (the whole point) and catching it as an error surfaces author
mistakes. Coverage models real-world absence that ignores the working calendar. A labeled
section with no label is pointless.

**Trade-offs:** Adding IDs later is a schema addition (backward compatible). Non-overlap
forbids modeling "out AND traveling" simultaneously — accepted, segments are mutually
exclusive in time.

---

## 2026-07-03 05:42:00 UTC — Rendered as a band above the Gantt; extends the date axis

**What:** The coverage band renders **above** the task rows as its own section. The viewer's
date axis **extends** to include coverage segments that fall outside the task date range.

**Why:** Availability is context read before the work timeline. Extending the axis guarantees
coverage is always fully visible; if that stretches the chart too far, the author simply
shortens the last segment. `project_finish` stays computed from work items only — only the
*viewer axis* extends, so the pure-work finish number is unaffected.

**Trade-offs:** A stray far-future coverage segment widens the whole chart. Acceptable and
author-controllable. The viewer's date-range scan must include coverage while
`project_finish` must not — two ranges, kept distinct.

---

## 2026-07-03 05:42:00 UTC — Single neutral color, new legend entry; truncate labels with tooltip

**What:** All coverage segments use one neutral color, **distinct** from every color already
in the chart (task/group/milestone/critical/link), added to the **legend**. Segment labels
truncate to fit the box and show the full text in a **hover tooltip** (`title`).

**Why:** Labels carry the meaning, not color, so one color suffices for v1; a distinct hue and
a legend entry keep coverage visually separate from work bars. Truncate+tooltip handles long
labels ("traveling to Santa Clara") in short segments without overflow.

**Trade-offs:** No per-label color coding yet (could add later). Very short segments show a
truncated or empty-looking label until hovered — acceptable for v1.

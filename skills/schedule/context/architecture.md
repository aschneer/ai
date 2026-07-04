# Architecture

How the Schedule skill is **built** — engineering structure and implementation choices. What the product does and the rules it enforces are in `prd.md` (requirements) and `data_model.md` (file shape); how a user or agent runs it is in `README.md` and `SKILL.md`. This document does not restate those; it covers code.

The deliverable is an **AI agent skill** (`SKILL.md` + Python libraries + JSON Schema files), not a standalone application.

---

## Design principles (engineering)

1. **Minimal code** — prefer instructing the agent via the skill unless correctness requires library code
2. **Modular libraries** — small, composable, unit-testable modules; thin CLIs
3. **Deterministic scheduling** — CPM and calendar math in Python, never LLM inference
4. **Read-only engine** — libraries validate and compute; they never write schedule/calendar YAML
5. **Validate first** — structural + logic validation before compute (see below)

---

## Agent vs deterministic code

The agent/library responsibility split is defined in **`prd.md`** § Agent vs deterministic code. The one engineering rule: before adding library code for a new capability, ask whether the skill can instruct the agent instead — prefer code only where correctness requires it (validation, graph algorithms, calendar math, rendering).

---

## Validation: validate first, compute on clean input

| Layer | Module | Purpose | On failure |
|-------|--------|---------|------------|
| **Structural** | `validate_lib.py` | JSON Schema — shape, required/forbidden fields, kinds | List every schema error; stop |
| **Logical** | `logic_validate_lib.py` | IDs, predecessor refs, cycles, listing rules, milestone working days, milestone deadline predecessors (FS-only) + deadline reachability, project-finish milestone (at most one, predecessors required), pinned bounds, milestone reachability | List every logic error; stop |
| **Compute** | `compute_lib.py` | CPM forward pass | Assumes valid input; no warnings channel |

Compute does not paper over bad data. Collect **all** validation errors before returning.

Example messages:

```
schedule: items: duplicate id 1: 'First' and 'Duplicate'
schedule: item 5: predecessor 99: unknown task id
schedule: milestone 13: date 2026-06-20 falls on a non-working day
schedule: milestone 13: date 2026-06-20 cannot be reached — predecessor chain for item 14 finishes 2026-06-23
schedule: milestone 50: deadline 2026-06-19 missed — predecessor 42 finishes 2026-06-24
schedule: cyclic predecessor dependency: 1 → 2 → 1
```

### Why JSON Schema (not Pydantic)

Schemas live in `schemas/*.schema.yaml` (JSON Schema authored in YAML). Same schemas validate in the editor (Red Hat YAML) and at runtime via `jsonschema`. Logic that needs the calendar or graph walks stays in Python to avoid drift and duplicate models.

### Adding a new rule

1. Structural → schema; logical → `logic_validate_lib.py`
2. Document in `data_model.md`
3. Test in `tests/test_logic_validate_lib.py`
4. Do **not** add defensive handling in `compute_lib.py`

---

## Scheduling pipeline

1. `load_schedule_project()` — load YAML, run schema + logic validation
2. `compute_schedule()` — CPM forward pass, critical path, project finish. When a milestone is designated `type: project_finish`, the critical path is the zero-slack chain feeding it (empty on buffer) and project finish is that chain's actual finish; otherwise the longest path to the latest computed finish. See `decisions.md` ADR-005.
3. `computed_schedule_to_dict()` — JSON for stdout and Gantt

Algorithm detail: `scheduling_algorithm.md`.

---

## Gantt output (implementation)

`gantt_lib.py` writes **`site/gantt_data.json`** (the serialized computed schedule) and copies the static viewer assets (`gantt.html`, `gantt.js`, `gantt_theme.css`) into **`site/`**. The viewer fetches `gantt_data.json` over HTTP, so it must be served — `file://` does not work; the server is Python `http.server` (no Vite/Node). The output dict shape is locked by `tests/test_compute_lib.py`; user-facing CLI flags and viewing are in `README.md`; the chart's required features are PRD R9/R24/R25/R26.

**Rendering:** item labels and the week header are HTML; the timeline column is a **single SVG** (`.timeline-svg`) holding task bars, group bracket paths, milestone markers, and dependency links in one coordinate system — required for faithful browser print. See **`decisions.md` ADR-002** (single SVG) and **ADR-001** (Python server, no Vite).

### Timeline positioning: the master grid

Every horizontal position in the timeline — task bar, group bracket, milestone marker, context segment — derives from **one source of truth: the rendered day columns of the HTML week header.** Bars never compute their own scale; they read where the header already painted each day. This is why bars stay aligned with their dates at any width. See **`decisions.md` ADR-004**.

**The one knob — `--day-w`.** The theme sets a single CSS variable for the width of one day column. The header grid is `grid-template-columns: repeat(--day-count, var(--day-w))`; the whole timeline width and `.gantt-inner` width derive from it. Changing `--day-w` (and re-rendering) rescales the entire chart — the intended hook for a future horizontal zoom / fit-to-viewport control.

**Day-index metrics, not pixels or percentages.** `spanMetrics()` converts a start/finish date to integer `{offsetDays, spanDays}` relative to the range start. No percentage-of-width, no per-item pixel math. These integers are unit-free and survive any `--day-w`.

**Edge measurement — `dayColumnEdges()`.** After the header is in the DOM, this reads each day column's actual painted left edge (plus the final right edge) into an array `edges[0..N]`, relative to the timeline origin. Because it measures what the browser rendered, it captures the browser's own sub-pixel rounding of fractional-rem columns — so bars snap to the *real* columns, not an idealized grid. The array is built **once per render** in `renderGantt()` and passed to both the context bands (people/events) and the SVG; nothing re-measures.

**Placement.** Every graphic is `edges[offsetDays]` to `edges[offsetDays + spanDays]` (clamped to the last edge). Task/group/milestone geometry (`barGeometry()`) and context segments (`renderContextSegment()`) use the identical lookup; the SVG's own width is `edges[last]`. One array, one formula, zero independent scales.

**Why this shape.** The prior viewer positioned bars as a percentage of a *measured* timeline width while the header used a CSS grid with a `minmax()` floor. When the floor clamped, the two widths diverged and bars drifted from their dates — the error accumulating rightward. Collapsing everything onto the header grid removes the second scale entirely. Full history and rejected alternatives: **`decisions.md` ADR-004**.

### Hover tooltips

Every bar, milestone, and context segment shows a hover tooltip. Content by kind: task/group → name, working-day count, calendar-day count (three lines); milestone → name and date (two lines); people/events segment → band name, segment label, and date range (three lines). Dates format as `mm/dd/yyyy`. Required content is specified in PRD **R29**.

**Business logic in Python; JS only renders.** The day counts are *not* computed in the browser — the viewer has no holiday calendar, so a JS working-day count would miscount tasks spanning a holiday. Instead `computed_schedule_to_dict()` writes **`working_days`** (via `calendar.count_working_days`, excluding weekends and holidays) and **`calendar_days`** (`finish - start + 1`) onto every item. `gantt.js` reads those fields verbatim. This is the general rule for the viewer: any derived value lives in the computed JSON, never in render code.

**Mechanism.** One floating `.gantt-tooltip` element, bound once on the document; any element carrying a `data-tip` attribute (newline-separated lines) triggers it. Bars are inside the SVG, which is `pointer-events: none` for scroll passthrough, so `.bar` elements re-enable `pointer-events: auto`. A group's bracket outline is too thin to hover reliably, so a transparent full-span hit rect behind it carries the tooltip.

### Cursor crosshair

A subtle vertical line (`.gantt-crosshair`, PRD **R30**) follows the cursor across the plot so a bar can be lined up with the date header. It is one `position: fixed` element bound once on `.gantt` and driven by `clientX` — being fixed and cursor-relative, it needs no scroll math (the line sits under the cursor regardless of scroll offset). It hides over the sticky label column (`clientX` within `--label-width` of the container's left edge) and whenever the cursor leaves the plot.

### Current-date indicator

An amber vertical line labeled "Today" (`.today-overlay` / `.today-line`, PRD **R31**) marks the current date. The line is drawn in its **own overlay SVG** (`renderTodayOverlay`) at `edges[todayOffset]` — the same master-grid lookup as every bar, so it aligns with the date header and scrolls with the content. `todayColumnOffset()` computes today from `new Date()` **at render time** (today is a property of *when the chart is viewed*, not a compute-time value, so it is never baked into `gantt_data.json`) and returns `null` when today falls outside `[range.start, range.end]`. Because `dateRange()` derives the axis only from item, people, and events dates, today never extends the range — an out-of-range today simply draws nothing, and a schedule opened long after it ended keeps its own width.

**Layering — the two-plane problem.** The line must sit *above every row, including a locked context band* (high `z-index`), yet *never paint over the sticky left label column*. A single row-based z-index can't satisfy both (the label column and a locked band want opposite orderings). The overlay resolves it by decoupling z from geometry: it carries a high z-index (above the locked context band), and a scroll-driven **`clip-path`** removes its leftmost `scrollLeft` px — exactly the strip the sticky label column covers — so the line is clipped out of the label column and vanishes once today's column scrolls fully behind it. The "Today" **tag** is a separate HTML element in the sticky annotation lane, so it stays pinned under the date header on vertical scroll while the line scrolls with the content.

### Compact rows (PRD R33)

Each row is one line tall. The label (`.label-text`) is a flexbox with the item name (`flex: 1`, truncates first) and the date range side by side; the dates use `mm/dd/yy` (`shortDate()`), while the hover tooltip keeps full `mm/dd/yyyy`. Row `min-height` and label padding are kept tight. Collapsing the previous two-line (name-over-dates) label to one line is the dominant vertical saving.

**Annotation lane.** A thin row (`.row.gutter`) sits between the date header and the first content row — a reserved, sticky strip for chrome that would otherwise overlap content or cost a whole row. It hosts two things today: the **"Today" tag** in its timeline cell (centered in the band between header bottom and lane bottom, with the line starting at the lane bottom), and the **Context section controls** in its label cell (collapse chevron, a standout "Context" chip, and the lock toggle). Being sticky under the header, both stay visible while scrolling — so the context band can be collapsed/expanded without scrolling back to the top. The lane is general-purpose, not tied to any one feature.

---

## Module layout

```
src/schedule/
  validate.py, compute.py     # CLIs
  validate_lib.py
  logic_validate_lib.py
  io_lib.py
  compute_lib.py
  gantt_lib.py
  calendar_lib.py
  predecessors_lib.py
  assets/                     # gantt.html, gantt.js, gantt_theme.css
schemas/
tests/
```

`validate` — validation only. `compute` — validate + compute + Gantt deploy + serve.

---

## Related references

- `prd.md` — product requirements (what)
- `data_model.md` — YAML editing reference
- `scheduling_algorithm.md` — CPM steps
- `decisions.md` — ADRs (Gantt stack, single SVG timeline, no Vite, etc.)
- `task_timing_modes.md` — pinned-date feature (R19–R23)
- `glossary.md` — glossary

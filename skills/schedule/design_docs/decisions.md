# Decisions

Architecture and product choices for the Schedule skill. New ADRs at the top; resolved product decisions are the audit trail for choices once captured in the PRD open-questions list.

---

## Resolved product decisions

Historical checklist — decisions now reflected in `prd.md`, `data_model.md`, or ADRs below.

| Topic | Decision |
|-------|----------|
| Predecessor format | Inline YAML list of MS Project strings (`["5FS", "7SS+2d"]`) |
| Identifier type | Stable integer Unique ID; **ID 0** reserved for project start milestone |
| Duration units (MVP) | Days and weeks only (`4d`, `2w`); hours out of scope |
| Calendar (MVP) | Weekends (Sat/Sun) and holidays excluded; separate `calendar.yaml` |
| Predecessors on groups | Allowed; constrains earliest child start (local project start) |
| Group children | Minimum 1 child, enforced at schema level |
| Item discriminator | `kind` is first field; values `milestone`, `task`, `group` |
| Group kind name | **`group`** (not `summary`, `phase`, etc.) — MS Project “summary task” |
| Predecessor listing | Immediate predecessors only; `["0FS"]` alone OR other preds without `0FS`; child with no preds uses `{parentId}SS` |
| Child→parent link | Start-to-start: `{parentId}SS` |
| Milestones | User `date` authoritative; no predecessors; only file-based date constraint |
| Validation | JSON Schema files in YAML; same schemas in editor and runtime |
| Holiday file location | Project directory; path relative to schedule file |
| Task timing modes | Implemented — §5; `timing` required on every task |
| Gantt output | Static HTML/JS/CSS + JSON in **`site/`** via `compute` |
| Gantt timeline rendering | Single SVG layer for bars + dependency links (print fidelity; ADR-002) |
| Gantt timeline positioning | Master grid — all graphics snap to measured header day columns; one `--day-w` knob (ADR-004) |
| Gantt charting library | Plain HTML/CSS/JS + SVG — no D3 (ADR-003) |
| Gantt viewing | HTTP URLs printed; user opens manually; network-reachable when remote |
| Critical path | Per-item marking in computed output and Gantt styling; zero-slack chain into a designated project-finish milestone, else longest path (ADR-005) |
| Project finish | `type: project_finish` milestone (opt-in, at most one) sets the deadline; reported finish = feeder chain's actual finish (MS Project model; ADR-005) |
| Schedule filename | Arbitrary; skill asks user for path |
| Engine mutability | Read-only on source YAML — validate, compute, write separate outputs only |
| Impossible schedules | **Hard errors** (§6.7), not warnings — no auto-fix |
| Deliverable | AI agent skill with composable libraries, not a standalone app |
| MVP | **Complete** (2026-06-14) — see `prd.md` status header; D.1 live refresh shelved |

### Group kind naming (§1.1 / schedule format)

Microsoft Project calls this a **summary task**. We use **`group`**: shorter, avoids confusion with report/summary language, reads naturally in YAML (`kind: group`). Rejected: `category`, `phase`, `section`, `container`, `rollup`, `block`, `package`, `summary`.

---

## ADR-001 — Static Gantt + Python dev server (no Vite)

**Date:** 2026-06-12  
**Status:** Accepted

### Context

The Gantt viewer is static HTML/JS served over HTTP. Users run `compute` locally or over SSH and need a single-click path to open the chart in a browser on their laptop.

### Decision

- **No Vite / Node frontend toolchain** for the skill.
- Keep **static assets** in `src/schedule/assets/`; `compute` copies them to the project’s **`site/`** directory with `gantt_data.json`.
- Serve with **Python `http.server`**, default bind **`0.0.0.0`** (`--host auto`), print **local + network** URLs; user opens manually (no auto-open).
- Optional **`SCHEDULE_VIEWER_HOST`** env var to override the network hostname (e.g. Tailscale DNS).

### Rationale

| Factor | Why not Vite | Why Python + static |
|--------|--------------|-------------------|
| Product shape | Skill + YAML + Python CPM; browser is read-only output | Matches “file is source of truth” |
| PRD minimal code | Second toolchain, build step, npm in a `uv` skill | One command: `uv run compute` |
| Hot reload (D.1) | HMR targets JS edits, not YAML→Python→JSON | Shelved — see `live_refresh.md` |
| Remote viewing | Vite’s win is `host: true` + URL list | Same pattern on `http.server` |

### Trade-offs

**Pros:** Simple install, portable static output, agent-friendly, no build drift.  
**Cons:** No HMR for viewer JS; manual refresh until D.1; binding `0.0.0.0` exposes the chart on the network (dev-only; use `--host 127.0.0.1` on untrusted hosts).

### Viewing paths (same as a Vite dev server)

1. **Network URL** — browser → server IP:port (LAN, Tailscale, or `SCHEDULE_VIEWER_HOST`).
2. **Local URL** — `127.0.0.1:port` on the laptop via Cursor/VS Code port forwarding or `ssh -L`.

### Revisit if

Interactive Gantt editing, a large SPA viewer, or a separate “schedule studio” app — then a frontend build tool may be justified (dev-only build into `assets/` at minimum).

---

## ADR-002 — Single SVG timeline layer for bars and links

**Date:** 2026-06-13  
**Status:** Accepted

### Context

PRD **§9.4** requires a printable Gantt: users must be able to print or export a faithful static copy (browser print/PDF or equivalent). The first viewer used HTML `%`-positioned bars with a separate overlay SVG for dependency links. That hybrid layout desynced under browser print preview and zoom — bars and links scaled independently.

### Decision

- Render **all timeline graphics in one SVG** (`.timeline-svg`): task rects, group bracket paths, milestone circles, and dependency link paths share one coordinate system and `viewBox`.
- Keep **HTML for labels** (item names, dates) and the week header; only the timeline column is SVG.
- Compute bar and link geometry from row layout + date metrics (not a second HTML bar layer).
- Add **`@media print`** CSS so the chart prints without clipping; defer server-side PDF generation.

### Rationale

| Factor | Hybrid HTML + SVG overlay | Single SVG timeline |
|--------|---------------------------|---------------------|
| Print fidelity (§9.4) | Bars and links drift apart when printed | One layer scales together |
| Complexity | Two rendering paths to keep aligned | One path for bars and links |
| On-screen | Worked until print/zoom | Same geometry for screen and print |
| Scope | — | Labels stay HTML; no full-page SVG rewrite |

### Trade-offs

**Pros:** Satisfies §9.4 with browser print; simpler mental model; MS Project–style bars/links stay aligned.  
**Cons:** SVG redraw on window resize; no drag-and-drop bar editing (already out of scope); server PDF still optional later.

### Revisit if

Print quality is insufficient (e.g. multi-page pagination, exact page sizing) — consider server-generated PDF or a print-specific layout pass without abandoning the single-SVG timeline for on-screen view.

---

## ADR-003 — No D3 for the Gantt viewer (MVP)

**Date:** 2026-06-13  
**Status:** Accepted

### Context

Freeze-pane scrolling and panning on the static Gantt viewer work acceptably with HTML/CSS sticky positioning and a single SVG timeline layer. D3 (or similar charting libraries) was considered for layout, zoom, and interaction.

### Decision

- **Do not add D3** (or another charting library) to the Gantt viewer for MVP.
- Keep the viewer as **static HTML/CSS + vanilla JS + SVG** copied from `src/schedule/assets/`.

### Rationale

| Factor | D3 / chart library | Current static viewer |
|--------|-------------------|------------------------|
| Dependencies | npm bundle, build or CDN | None — matches ADR-001 |
| Scrolling / pan | Powerful but adds API surface | CSS sticky + native scroll tested and sufficient |
| Print (§9.4) | Extra integration work | Single SVG already satisfies print fidelity |
| Skill shape | Second frontend stack in a Python skill | One `compute` deploy path |

### Trade-offs

**Pros:** Simpler toolchain, smaller assets, agent-friendly static output, no library lock-in.  
**Cons:** Manual geometry for bars/links; no built-in zoom brush or drag-edit (already out of scope).

### Revisit if

Interactive zoom/pan beyond native scroll, drag-to-reschedule, or a rich in-browser editing surface becomes in scope — then evaluate D3 or a focused timeline library behind the same static deploy model.

---

## ADR-004 — Master grid: all timeline graphics snap to measured header day columns

**Date:** 2026-07-03  
**Status:** Accepted

### Context

Task bars were misaligned with their dates in the week header, and the error grew worse toward the right of the chart. Two independent horizontal scales had drifted apart:

- The **header** used a CSS grid, `repeat(N, minmax(1.1rem, 1fr))`. On any realistic width the `minmax` **floor** clamped each column to `1.1rem`, so the header laid out at its floored total (e.g. 3167px for 180 days).
- The **bars** were positioned as a **percentage** of a *measured* `.timeline` width sampled early (e.g. 3056px), placed into a single SVG whose `viewBox` used that same measured width.

`3056 ≠ 3167`, so bar day *d* landed at `(d/N)·3056` while header day *d* sat at `d·17.6px`. The per-day gap accumulated linearly — imperceptible at day 0, ~150px by day 180. Browser-zoom-invariant (both scales are rem/px and zoom together), which is why zooming did not change the misalignment. Measured with Playwright: 152px drift at day 179; 0px after the fix.

### Decision

Position **everything from one source of truth: the rendered header day columns.**

- **One knob — `--day-w`.** A single CSS variable defines a day column's width. Header grid is `repeat(--day-count, var(--day-w))` — **no `minmax` floor**. Timeline and `.gantt-inner` width derive from it.
- **Day-index metrics.** `spanMetrics()` returns integer `{offsetDays, spanDays}`; no percentages, no per-item pixels.
- **Measured edges.** `dayColumnEdges()` reads each painted column's actual left edge (plus final right) into `edges[0..N]` once per render, after the header is in the DOM.
- **One placement formula.** Bars, group brackets, milestones (`barGeometry()`), and context segments (`renderContextSegment()`) all map `offsetDays…offsetDays+spanDays` through `edges`. The SVG width is `edges[last]`. No graphic computes its own scale.

### Rationale

| Factor | Percentage-of-measured-width (old) | Master grid (edges) |
|--------|-----------------------------------|---------------------|
| Sources of truth | Two (header grid + bar %); drift when they disagree | One (header columns) |
| The bug | Floor clamp desyncs the two widths → rightward drift | Structurally impossible — bars read the header |
| Fractional widths | Percentage vs floored grid rounds differently | Edges capture the browser's own rounding; 0px residual |
| Future horizontal zoom | Every scale must be kept in sync by hand | Change `--day-w`, re-render; alignment holds |

Measuring the *rendered* edges (rather than recomputing `offsetDays·day-w` in JS) is deliberate: fractional-rem columns are pixel-snapped unevenly by the browser, so a recomputed grid re-introduces sub-pixel drift. Reading the painted edges inherits the exact rounding. Verified 0px residual at `--day-w` of 0.7rem, 3.3rem, and 41px.

### Trade-offs

**Pros:** One scale eliminates the whole class of drift bugs; correct at any (including fractional) day width; `--day-w` is a ready-made zoom hook.  
**Cons:** Bars depend on a layout read (`getBoundingClientRect`) of the header, so the header must be in the DOM before the SVG renders (it is — `renderGantt()` builds the header, then the edges, then the band and SVG). One forced layout per render; negligible at these sizes.

### Revisit if

A horizontal zoom / fit-to-viewport control is built — it should drive `--day-w` (and re-render) rather than introduce any second positioning path. If rendering ever moves off a live DOM (e.g. server-side SVG), replace the measured-edge read with an explicit integer-px `--day-w` so columns land on whole pixels without measurement.

---

## ADR-005 — Project-finish milestone: the Microsoft Project model

**Date:** 2026-07-04  
**Status:** Accepted

### Context

The critical path needs a defined terminus. Two questions were open:

1. **What is "project finish"** — the latest computed finish, or a user-set deadline?
2. **When is a schedule critical** — always (longest path), or only at zero slack against a deadline?

A milestone can already carry a finish-to-start predecessor to mark a culminating deadline (§3.8.1), but a plain deadline milestone was self-marking its chain critical whenever the chain landed on the date — conflating "there is a deadline" with "the deadline is the project finish."

### Decision

Adopt the Microsoft Project separation: **finish = when work ends; deadline = a separate target.**

- **`type: project_finish`** designates at most one milestone as the project finish; it **must** list a predecessor chain (the culminating work). Absent = ordinary milestone.
- **Critical path** is the zero-slack chain feeding the designated milestone: critical when the chain finishes exactly on the date, **empty** when it finishes early (buffer). With no designated milestone, fall back to the longest path to the computed finish (prior behavior).
- **Reported project finish** = the feeding chain's **actual finish**, which may be **earlier** than the milestone's date. The milestone marker shows the deadline separately.
- **Plain deadline milestones no longer self-mark critical** — only the designated finish milestone does. `_deadline_milestone_terminals` removed.

### Rationale

| Question | MS Project answer | Our implementation |
|----------|-------------------|--------------------|
| Project finish value | Latest task finish (when work ends) | Feeder chain's actual finish |
| Deadline vs finish | Deadline is a separate marker, not the finish | Milestone date is the deadline; finish is the feeder finish |
| Critical path | Zero total slack | Zero-slack chain into the designated milestone |
| Ahead of deadline | Slack shown; no critical path forced | Empty critical path (buffer) |
| Missed deadline | Red flag | Hard error (§6.7, existing reachability) |

Requiring predecessors on the finish milestone matches how MS Project is used: a finish marker with nothing feeding it is meaningless (in MS Project it would float to project start). Our milestone dates are authoritative, so the marker still holds its date — but with no feeder there is no chain to be critical, so the requirement keeps it meaningful.

Choosing feeder-actual-finish over the milestone date as the reported finish is the crux: it means the reported finish can precede the deadline marker on the Gantt (buffer). That is intentional and correct — the project *finishes* when the work is done; the deadline is a commitment shown alongside, not the finish itself.

### Trade-offs

**Pros:** One coherent model (finish = work end, deadline = target); zero-slack criticality matches true CPM; removes the `_deadline_milestone_terminals` special case (net simpler). **Cons:** A user glancing at the Gantt sees the project-finish value left of the finish-milestone marker in the buffer case — needs the mental model that finish ≠ deadline. Documented in §3.9 / §6.8.

### Revisit if

Multiple project-finish milestones are ever wanted (currently capped at one), or if users need the reported finish to equal the committed deadline rather than the actual work end — that would be a different product stance (deadline-as-finish) and should be a deliberate reversal, not a drift.

---

## ADR-006 — Split "coverage" into "people" and "events"

**Date:** 2026-07-04  
**Status:** Accepted

### Context

The original `coverage` band held only personnel availability (vacations, out-of-office, work location). Users also want non-project calendar context that isn't tied to a person — company events, holidays of note, external dates — so a viewer understands what else is happening around the schedule. The name "coverage" was narrow and did not capture that second category.

### Decision

Replace the single `coverage` key with **two top-level keys, `people` and `events`**, of identical shape (`{name, segments: [{start, finish, label}]}`).

- **No container key, no per-band `kind`** — the top-level key *is* the type, so the shared shape needs no discriminator and the YAML stays flat.
- **One shared lock**: the lock toggle pins both bands (people rows, then events rows) below the header. Independent per-band locks were considered and rejected as not worth the sticky-stack and z-order complexity (YAGNI — the sub-typed data already partitions cleanly, so splitting the lock later is a viewer-only change).
- **Render order**: people on top, events below; two legend colors (people teal `--color-people`, events slate `--color-events`).
- Internally the shared render/validation mechanics use a neutral **`context`** term (`renderContextRow`, `_check_context_segments`, `.context-*` CSS); this is code-only and not user-facing.

### Rationale

Two flat keys beat a container + `kind` because the bands share one shape — a discriminator field would be pure ceremony. The name problem ("what umbrella term covers people *and* events?") disappears entirely: there is no umbrella, just two well-named keys. "Events" is the catch-all for any non-person context, so the two keys are exhaustive by construction.

### Trade-offs

**Pros:** Clearer intent (people vs events), two colors, exhaustive partition, no jargon umbrella term, minimal schema (two arrays sharing one entry def). **Cons:** Breaking rename — existing `coverage:` files must become `people:`. Acceptable: this is a skill, so all in-repo examples/fixtures/tests were migrated in the same change; no external data to migrate.

### Revisit if

Users need independent lock/scroll behavior per band (then split the one lock — data already supports it), or a third context category emerges that fits neither people nor events (add a third top-level key of the same shape).

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
| Task timing modes | Implemented — R19–R23; `timing` required on every task |
| Gantt output | Static HTML/JS + JSON in project directory via `compute` |
| Gantt timeline rendering | Single SVG layer for bars + dependency links (print fidelity; ADR-002) |
| Gantt charting library | Plain HTML/CSS/JS + SVG — no D3 (ADR-003) |
| Gantt viewing | HTTP URLs printed; user opens manually; network-reachable when remote |
| Critical path | Per-item marking in computed output and Gantt styling |
| Schedule filename | Arbitrary; skill asks user for path |
| Engine mutability | Read-only on source YAML — validate, compute, write separate outputs only |
| Impossible schedules | **Hard errors** (R18), not warnings — no auto-fix |
| Deliverable | AI agent skill with composable libraries, not a standalone app |

### Group kind naming (R1 / schedule format)

Microsoft Project calls this a **summary task**. We use **`group`**: shorter, avoids confusion with report/summary language, reads naturally in YAML (`kind: group`). Rejected: `category`, `phase`, `section`, `container`, `rollup`, `block`, `package`, `summary`.

---

## ADR-001 — Static Gantt + Python dev server (no Vite)

**Date:** 2026-06-12  
**Status:** Accepted

### Context

The Gantt viewer is static HTML/JS served over HTTP. Users run `compute` locally or over SSH and need a single-click path to open the chart in a browser on their laptop.

### Decision

- **No Vite / Node frontend toolchain** for the skill.
- Keep **static assets** in `src/schedule/assets/`; `compute` copies them to the user’s project directory with `gantt_data.json`.
- Serve with **Python `http.server`**, default bind **`0.0.0.0`** (`--host auto`), print **local + network** URLs; user opens manually (no auto-open).
- Optional **`SCHEDULE_VIEWER_HOST`** env var to override the network hostname (e.g. Tailscale DNS).

### Rationale

| Factor | Why not Vite | Why Python + static |
|--------|--------------|-------------------|
| Product shape | Skill + YAML + Python CPM; browser is read-only output | Matches “file is source of truth” |
| PRD minimal code | Second toolchain, build step, npm in a `uv` skill | One command: `uv run compute` |
| Hot reload (R10) | HMR targets JS edits, not YAML→Python→JSON | Shelved — see `live_refresh.md` |
| Remote viewing | Vite’s win is `host: true` + URL list | Same pattern on `http.server` |

### Trade-offs

**Pros:** Simple install, portable static output, agent-friendly, no build drift.  
**Cons:** No HMR for viewer JS; manual refresh until R10; binding `0.0.0.0` exposes the chart on the network (dev-only; use `--host 127.0.0.1` on untrusted hosts).

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

PRD **R26** requires a printable Gantt: users must be able to print or export a faithful static copy (browser print/PDF or equivalent). The first viewer used HTML `%`-positioned bars with a separate overlay SVG for dependency links. That hybrid layout desynced under browser print preview and zoom — bars and links scaled independently.

### Decision

- Render **all timeline graphics in one SVG** (`.timeline-svg`): task rects, group bracket paths, milestone circles, and dependency link paths share one coordinate system and `viewBox`.
- Keep **HTML for labels** (item names, dates) and the week header; only the timeline column is SVG.
- Compute bar and link geometry from row layout + date metrics (not a second HTML bar layer).
- Add **`@media print`** CSS so the chart prints without clipping; defer server-side PDF generation.

### Rationale

| Factor | Hybrid HTML + SVG overlay | Single SVG timeline |
|--------|---------------------------|---------------------|
| Print fidelity (R26) | Bars and links drift apart when printed | One layer scales together |
| Complexity | Two rendering paths to keep aligned | One path for bars and links |
| On-screen | Worked until print/zoom | Same geometry for screen and print |
| Scope | — | Labels stay HTML; no full-page SVG rewrite |

### Trade-offs

**Pros:** Satisfies R26 with browser print; simpler mental model; MS Project–style bars/links stay aligned.  
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
| Print (R26) | Extra integration work | Single SVG already satisfies print fidelity |
| Skill shape | Second frontend stack in a Python skill | One `compute` deploy path |

### Trade-offs

**Pros:** Simpler toolchain, smaller assets, agent-friendly static output, no library lock-in.  
**Cons:** Manual geometry for bars/links; no built-in zoom brush or drag-edit (already out of scope).

### Revisit if

Interactive zoom/pan beyond native scroll, drag-to-reschedule, or a rich in-browser editing surface becomes in scope — then evaluate D3 or a focused timeline library behind the same static deploy model.

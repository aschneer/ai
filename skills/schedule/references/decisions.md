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

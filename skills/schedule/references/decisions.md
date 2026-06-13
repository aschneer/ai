# Decisions

Architecture and product choices for the Schedule skill. New entries at the top.

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
| Hot reload (R10) | HMR targets JS edits, not YAML→Python→JSON | Poll JSON or `compute --watch` in Python later |
| Remote viewing | Vite’s win is `host: true` + URL list | Same pattern on `http.server` |

### Trade-offs

**Pros:** Simple install, portable static output, agent-friendly, no build drift.  
**Cons:** No HMR for viewer JS; manual refresh until R10; binding `0.0.0.0` exposes the chart on the network (dev-only; use `--host 127.0.0.1` on untrusted hosts).

### Viewing paths (same as a Vite dev server)

1. **Network URL** — browser → server IP:port (LAN, Tailscale, or `SCHEDULE_VIEWER_HOST`).
2. **Local URL** — `127.0.0.1:port` on the laptop via Cursor/VS Code port forwarding or `ssh -L`.

### Revisit if

Interactive Gantt editing, a large SPA viewer, or a separate “schedule studio” app — then a frontend build tool may be justified (dev-only build into `assets/` at minimum).

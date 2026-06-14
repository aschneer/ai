# Live refresh (PRD R10) — shelved implementation plan

**Status:** Shelved (2026-06-07)  
**PRD:** R10 — Live refresh (nice to have)  
**Decision:** Not needed for MVP. Manual browser refresh after re-running `compute` is acceptable.

---

## Goal

While developing a schedule, the user edits YAML, regenerates dates, and sees the Gantt update **without** manually refreshing the browser tab or juggling multiple terminals — if the UX cost of building and maintaining this is worth it.

---

## Current workflow (no live refresh)

1. Run `uv run compute path/to/schedule.yaml` (default: writes JSON, deploys viewer, serves project dir, blocks until Ctrl+C).
2. Open the printed Gantt URL once.
3. Edit `schedule.yaml` or `calendar.yaml`.
4. Ctrl+C the server (or use a second terminal with `compute --no-serve`).
5. Re-run `compute`.
6. **Refresh the browser** to load new `gantt_data.json`.

This is sufficient for occasional edits and agent-driven workflows.

---

## Why we shelved it

- Re-running `compute` already regenerates JSON and redeploys assets; the missing piece is only “don’t refresh the browser.”
- `--serve` blocks the terminal; avoiding a second terminal requires either `--watch` or accepting Ctrl+C loops.
- Browser polling alone doesn’t remove the need to re-run compute.
- `compute --watch` alone still needs browser polling (or manual refresh).
- Full loop is two mechanisms (Python watch + JS poll) for a dev-only convenience.
- Skill priority is text-native scheduling correctness, not a live dev studio.

**Revisit when:** frequent local iteration on Gantt + YAML in one session becomes a common pain point.

---

## How the tool knows what to watch

There is no project registry. Paths come from the **schedule file argument** to `validate` / `compute`:

| Path | Resolution |
|------|------------|
| Schedule file | CLI argument (any filename) |
| Project directory | `schedule_path.parent` — where Gantt artifacts are written and served |
| Calendar file | `calendar:` in schedule YAML, resolved relative to the schedule file (`io_lib.calendar_path_for_schedule`) |

A watcher should monitor **resolved file paths**, not “scan a directory”:

- `ScheduleProject.schedule_path`
- `ScheduleProject.calendar_path` (if present)

Re-resolve `calendar_path` after each successful reload in case `calendar:` changed in the schedule file.

Ignore generated artifacts (`gantt_data.json`, `gantt.html`, `gantt.js`) to avoid feedback loops.

---

## Proposed architecture (two layers)

```text
  schedule.yaml ──► compute (validate + CPM) ──► gantt_data.json
        ▲                      ▲                        │
        │                      │                        │
   [--watch]              [manual or                  [browser poll]
   mtime/inotify           --watch]                        │
        │                      │                        ▼
        └──────────────────────┘                  gantt.js re-render
```

### Layer 1 — Browser poll (`gantt.js`)

**Purpose:** Open Gantt tab once; pick up new JSON without F5.

- Poll `gantt_data.json` every ~2s with `fetch(..., { cache: "no-store" })`.
- Compare `JSON.stringify(data)` to last snapshot; re-render on change.
- Preserve scroll position across re-renders.
- On poll failure: `console.warn` only; keep showing last good chart.
- On initial load failure: show error banner (current behavior).

**Does not:** Run compute, watch YAML, or restart the server.

**Paired workflow:** Terminal A serves; Terminal B runs `compute --no-serve` after edits.

### Layer 2 — `compute --watch` (CLI)

**Purpose:** One terminal; auto-regenerate JSON when input YAML changes.

```bash
uv run compute path/to/schedule.yaml --watch
```

**Behavior:**

1. Initial validate + compute → write `gantt_data.json`, deploy viewer assets once.
2. Start HTTP server on a **daemon thread** (main thread runs watch loop), or equivalent.
3. Poll mtimes of `schedule_path` and `calendar_path` every ~1s (stdlib — no new dependency).
4. Debounce saves (~300–500ms) so partial editor writes don’t spam compute.
5. On change: `load_schedule_project` → compute → overwrite `gantt_data.json`.
6. On validation error: print errors to stderr; **keep last good JSON** in the chart.
7. Redeploy `gantt.html` / `gantt.js` on startup only (not every recompute).

**Flags:**

| Command | Behavior |
|---------|----------|
| `compute` (today) | Once + serve |
| `compute --watch` | Watch + serve |
| `compute --watch --no-serve` | Watch only (niche) |

**Implementation sketch:** `watch_lib.py` with mtime polling + debounce; wire into `compute.py` when `--watch` is set.

### Full loop

`compute --watch` + browser poll = edit YAML → JSON updates → chart updates, one terminal, one tab.

---

## Files to touch (when implementing)

| Piece | Files |
|-------|--------|
| Browser poll | `src/schedule/assets/gantt.js` |
| CLI watch | `src/schedule/compute.py`, new `watch_lib.py`, tests |
| Docs | `SKILL.md`, `architecture.md`, `decisions.md`, `projects/260607_1700_project_schedule/260611_2358_remaining_tasks.md` |
| Tests | `test_gantt_lib.py` (deployed JS contains poll constant); `test_watch_lib.py` (mtime/debounce with tmp paths) |

---

## Terminal UX (when implemented)

```text
ok: gantt_data.json
ok: gantt.html
ok: gantt.js
Gantt chart (local): http://127.0.0.1:8000/gantt.html
Serving .../farmers_market on 0.0.0.0:8000 (Ctrl+C to stop)
watching schedule.yaml, calendar.yaml

# user saves schedule.yaml
ok: recomputed (project_finish 2026-07-08)

# user saves invalid YAML
error: task 42: ...
(watching; last good gantt_data.json unchanged)
```

---

## Explicitly not in scope for this plan

- Watching directories or unrelated YAML files
- Hot reload of viewer JS/CSS (re-run `compute` once to redeploy assets)
- File watcher dependency (`watchdog`) unless stdlib polling proves too slow
- Auto-opening the browser
- Replacing separate `validate` / `compute` commands

---

## Related docs

- `prd.md` — R10 requirement
- `decisions.md` ADR-001 — Python static server vs Vite
- `architecture.md` — Gantt output and serve flags

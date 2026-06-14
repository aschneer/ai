# Architecture

How the Schedule skill is built. **Hard requirements** (file format, behavior): `prd.md`. **Editing examples**: `data_model.md`.

**MVP status:** Complete (2026-06-14). See `prd.md` § MVP status.

---

## Deliverable

An **AI agent skill** (`SKILL.md` + Python libraries + JSON Schema files), not a standalone application. Users and agents edit YAML in a project directory; libraries validate, compute, and render.

---

## Design principles (engineering)

1. **Minimal code** — prefer instructing the agent via the skill unless correctness requires library code
2. **Modular libraries** — small, composable, unit-testable modules; thin CLIs
3. **Deterministic scheduling** — CPM and calendar math in Python, never LLM inference
4. **Read-only engine** — libraries validate and compute; they never write schedule/calendar YAML
5. **Validate first** — structural + logic validation before compute (see below)

---

## Agent vs deterministic code

Defined in **`prd.md`** § Agent vs deterministic code. Implementation notes:

- When validation fails, list every error before the agent edits YAML (unless the user already asked for fixes).
- Before adding library code for a new capability, ask whether the skill can instruct the agent instead — prefer code only where correctness requires it (validation, graph algorithms, calendar math, rendering).

---

## Project directory

```
my-project/
  schedule.yaml      # any filename
  calendar.yaml      # path relative to schedule file
  gantt_data.json   # generated
  gantt.html        # generated (copied from skill assets)
  gantt.js
```

The skill asks for the schedule file or project directory. All artifacts for one schedule stay co-located.

---

## Validation: validate first, compute on clean input

| Layer | Module | Purpose | On failure |
|-------|--------|---------|------------|
| **Structural** | `validate_lib.py` | JSON Schema — shape, required/forbidden fields, kinds | List every schema error; stop |
| **Logical** | `logic_validate_lib.py` | IDs, predecessor refs, cycles, listing rules, milestone working days, pinned bounds, milestone reachability | List every logic error; stop |
| **Compute** | `compute_lib.py` | CPM forward pass | Assumes valid input; no warnings channel |

Compute does not paper over bad data. Collect **all** validation errors before returning.

Example messages:

```
schedule: items: duplicate id 1: 'First' and 'Duplicate'
schedule: item 5: predecessor 99: unknown task id
schedule: milestone 13: date 2026-06-20 falls on a non-working day
schedule: milestone 13: date 2026-06-20 cannot be reached — predecessor chain for item 14 finishes 2026-06-23
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

## Data model (implementation)

Three **`kind`** values: `milestone`, `task`, `group`. The `kind` field is first on every item and drives which other fields are legal. **`group`** = Microsoft Project summary task.

Full field constraints, predecessor listing rules, and examples: **`data_model.md`**.

---

## Scheduling pipeline

1. `load_schedule_project()` — load YAML, run schema + logic validation
2. `compute_schedule()` — CPM forward pass, critical path, project finish
3. `computed_schedule_to_dict()` — JSON for stdout and Gantt

Algorithm detail: `scheduling_algorithm.md`.

---

## Gantt output

**`compute`** (default):

1. Validates (as above)
2. Runs CPM
3. Writes **`gantt_data.json`** (items with start, finish, duration, `is_critical`, parsed `predecessors`, etc.)
4. Copies static **`gantt.html`** + **`gantt.js`** from `src/schedule/assets/` into the project directory
5. Prints JSON to stdout (default `--stdout`)
6. Optionally serves the project directory (default `--serve`)

The viewer fetches `gantt_data.json` over HTTP — `file://` does not work.

**Rendering:** Item labels and the week header are HTML. The timeline column is a **single SVG** (`.timeline-svg`) containing task bars, group bracket paths, milestone markers, and dependency links in one coordinate system — required for faithful browser print (PRD R26). See **`decisions.md` ADR-002**.

Viewer features: task/group bars, milestones, SVG dependency links (FS/SS/FF/SF anchors), critical bar styling, print-friendly layout.

---

## Dev server and viewing

Implemented in `gantt_lib.py` with Python `http.server` (no Vite/Node). See **`decisions.md` ADR-001**.

| CLI | Behavior |
|-----|----------|
| `--host auto` (default) | Bind `0.0.0.0`; print local + network URLs |
| `--host 127.0.0.1` | Loopback only |
| `--no-serve` | Write files only (CI) |
| `--port` | Default 8000 |

Prints clickable **local** (`127.0.0.1`) and **network** (LAN IP or `SCHEDULE_VIEWER_HOST`) URLs. User opens manually — no auto-open. Over SSH, local URL works with Cursor/VS Code port forwarding or `ssh -L`.

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
  assets/                     # gantt.html, gantt.js
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
- `context.md` — glossary

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

## Scheduling pipeline

1. `load_schedule_project()` — load YAML, run schema + logic validation
2. `compute_schedule()` — CPM forward pass, critical path, project finish
3. `computed_schedule_to_dict()` — JSON for stdout and Gantt

Algorithm detail: `scheduling_algorithm.md`.

---

## Gantt output (implementation)

`gantt_lib.py` writes **`site/gantt_data.json`** (the serialized computed schedule) and copies the static viewer assets (`gantt.html`, `gantt.js`, `gantt_theme.css`) into **`site/`**. The viewer fetches `gantt_data.json` over HTTP, so it must be served — `file://` does not work; the server is Python `http.server` (no Vite/Node). The output dict shape is locked by `tests/test_compute_lib.py`; user-facing CLI flags and viewing are in `README.md`; the chart's required features are PRD R9/R24/R25/R26.

**Rendering:** item labels and the week header are HTML; the timeline column is a **single SVG** (`.timeline-svg`) holding task bars, group bracket paths, milestone markers, and dependency links in one coordinate system — required for faithful browser print. See **`decisions.md` ADR-002** (single SVG) and **ADR-001** (Python server, no Vite).

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

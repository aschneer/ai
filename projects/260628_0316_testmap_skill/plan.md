# Testmap — Implementation Plan

**Date:** 2026-06-28  
**Goal:** Implement the testmap skill per `skills/testmap/design_docs/prd.md` — a tool that audits test suites for assertion quality, input coverage, and behavioral completeness, producing a rich HTML gap report.

---

## Approach

Work top-down: design before code. Establish the data model first (JSON schemas), then implement scripts against those schemas, then the agent instructions, then the report.

The existing scripts (`build_index.py`, `triage.py`, `find_stale.py`, `report.py`, `run_mutation.py`) are a working prototype that implements a subset of the PRD. The reimplementation reuses their core logic but extends them significantly. Rewrite, don't patch.

---

## Phase 1 — Architecture and data model

### 1.1 Architecture doc
Write `skills/testmap/design_docs/architecture.md` covering:
- Component map: which scripts exist, what each does, what it reads/writes
- Data flow diagram: user invocation → index → triage → user confirmation → analysis → report
- Agent/code boundary: what the agent does (behavioral analysis, testability rating, spec inference) vs. what code does (symbol discovery, hashing, triage scoring, report rendering)
- Output directory layout (`testmap_output/` contents)

### 1.2 JSON schemas
Write `skills/testmap/design_docs/schemas/` containing:
- `index_schema.json` — per-symbol entry in `index.json` (all fields from PRD §2.3 + triage fields from PRD §4.3)
- `analysis_schema.json` — per-symbol entry in `analysis.json` (all fields from PRD §6.8)
- `meta_schema.json` — `meta.json` (all fields from PRD §9.3)

Schemas are the contract between scripts and agent. Scripts validate output against schemas before writing.

---

## Phase 2 — Scripts

### 2.1 `build_index.py`
Changes from current:
- Output to `<target_dir>/testmap_output/index.json` (was `.coverage_cache/`)
- New symbol fields: decorator/annotation list (§2.3.11), visibility/access modifier (§2.3.12), is-test-file flag (§2.3.13)
- Validate output against `index_schema.json`

### 2.2 `triage.py`
Changes from current:
- New signals: no-analysis flag (§4.1.6), public API visibility (§4.1.7)
- Write raw signal values per signal to `index.json` alongside bucket and composite score (§4.3)
- After scoring, print pre-analysis summary (§4.4): symbol counts by kind and priority, stale vs. new vs. current, scope warning for large codebases
- Prompt user for scope confirmation (§4.5–4.6) and return chosen scope

### 2.3 `find_stale.py`
Changes from current:
- Read from `testmap_output/` (was `.coverage_cache/`)
- Output is consumed by triage (folded into pre-analysis summary)

### 2.4 `run_mutation.py`
Minor changes:
- Read/write from `testmap_output/`
- Validate mutation results against `analysis_schema.json`

### 2.5 `report.py`
Full rewrite — current version outputs plain text only. New version:
- Reads `index.json`, `analysis.json`, `meta.json`
- Produces `testmap_output/report.html` — self-contained, no external dependencies
- Implements all sections from PRD §8.2 in order:
  1. Hero summary (composite score, grade, metadata, narrative)
  2. KPI strip
  3. Coverage heatmap
  4. Risk vs. coverage scatter plot
  5. Files needing attention table
  6. Brittle test distribution
  7. Test difficulty distribution
  8. Findings — what to fix
  9. Unspecified behaviors table
  10. Agent insights (placeholder section; content written by agent into `analysis.json`)
  11. Test prescription table
  12. Symbol coverage matrix (nested: module → symbol → behavior cell)
  13. Footer
- Must be fully regenerable from output files alone (§8.3)

---

## Phase 3 — Agent instructions

### 3.1 Update `SKILL.md`
Rewrite agent instructions to reflect new PRD:
- Invoke `build_index.py`, then `find_stale.py`, then `triage.py`
- Present pre-analysis summary; wait for user confirmation of scope
- Warn user before overwriting existing `testmap_output/` (§9.4)
- For each symbol in confirmed scope:
  - Run testability analysis (§5) and write to `analysis.json`
  - Run behavioral analysis (§6): infer spec, walk edge-case taxonomy, build behavior matrix, map tests, classify cells
  - Write full analysis entry per §6.8 schema
- Optionally run `run_mutation.py` per symbol
- Run `report.py` to generate HTML report
- Copy `README_template.md` to `testmap_output/README.md`

### 3.2 Write `README_template.md`
Static file stored in `skills/testmap/`, copied verbatim to `testmap_output/` on every run. Content per PRD §10.3.

---

## Phase 4 — Validation

### 4.1 End-to-end test
Run testmap against a real codebase with known test coverage characteristics. Verify:
- `index.json` contains all expected symbols with correct fields
- Triage scores make intuitive sense
- Analysis entries match schema
- HTML report renders correctly and all sections are populated
- Re-running without code changes does not re-analyze unchanged symbols

### 4.2 Schema validation
Verify all scripts validate their output against schemas before writing.

---

## Open questions / decisions to make during implementation

- **Agent insights section**: how does the agent write free-form insights into the report? Options: (a) agent writes an `insights` field to `analysis.json` at a global level, `report.py` renders it; (b) agent writes raw HTML/Markdown fragment that `report.py` injects. Option (a) is cleaner.
- **Chart rendering**: HTML report needs charts (heatmap, scatter plot, bar charts) with no external dependencies. Options: inline SVG generated by `report.py`, or a small vendored JS charting library bundled inline. Decide during Phase 2.5.
- **Scope of rewrite vs. incremental patch**: current scripts are functional prototypes. Recommend full rewrite for cleanliness, but this is a judgment call during implementation.

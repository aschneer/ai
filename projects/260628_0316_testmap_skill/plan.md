# Testmap — Implementation Plan

Ordered task list only. WHAT to build and the rules live in
`skills/testmap/design_docs/{prd,architecture,decisions}.md`. This doc tracks
order and status — it deliberately holds no design detail, so it can't drift
out of sync with the design docs.

Status: `[ ]` todo · `[~]` in progress · `[x]` done

## Phase 1 — Project skeleton
- [x] UV project: `pyproject.toml`, `src/testmap/`, `[project.scripts]` (architecture §6)
- [x] `schemas/*.schema.yaml` for every pipeline file (architecture §5)
- [x] `schema_lib` + `paths_lib` (shared load/validate/path resolution)

## Phase 2 — Pipeline code
- [x] Stage 1 `discover` → `index.json` (architecture §4)
  - [x] `languages_lib` (per-language node kinds, keywords, mutation tools)
  - [x] `discover_lib` (tree-sitter walk, symbol extraction, hashing)
  - [x] `index_lib` (incremental merge, symbol-ID minting, load/save)
  - [x] `discover.py` (thin CLI)
- [x] Stage 2 `triage` → `triage.json` (`churn_lib`, `triage_lib`, `triage.py`)
- [ ] Stage 3 `staleness` → `scope.json`
- [ ] Stage 5 `mutate` → `mutation.json` (optional)
- [ ] Stage 6 `report` code half: composite score + grade, `meta.json`
- [ ] `analysis_cli.py` + `analysis_lib` (validate/assemble agent output; PRD §11)

## Phase 3 — Report rendering layer
- [ ] Static assets: `report.html`, `render.js`, bundled `chart.js` + `marked.js` (PRD §8)
- [ ] `render.js` builds all PRD §8.2 sections from the data files

## Phase 4 — Agent + supporting files
- [ ] `SKILL.md`: drive pipeline, scope confirmation, per-symbol analysis (PRD §5–6), `report_content.json`
- [ ] `README_template.md` (PRD §10)
- [ ] `edge_case_taxonomy.md`, `sensitivity_keywords.md`

## Phase 5 — Validation
- [ ] End-to-end run on a real repo; verify all sections populate, incremental re-run skips unchanged symbols
- [ ] Schema validation enforced at every stage boundary

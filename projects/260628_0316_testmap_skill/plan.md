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
- [x] Stage 3 `staleness` → `scope.json` (`staleness_lib`, `staleness.py`; output `.gitignore`)
- [~] Stage 5 `mutate` → `mutation.json` (optional) — DEFERRED (PRD D.2)
- [x] Stage 6 `report` code half: composite score + grade, `metrics.json`, `meta.json` (`report_lib`, `report.py`)
- [x] `analysis_lib` + `analysis_cli.py` (write) + `query.py` (read-only) (PRD §11)

## Phase 3 — Report rendering layer
- [x] Static assets: `report.html`, `report.css`, `render.js`, bundled `chart.js` + `marked.js` (PRD §8)
  - [x] vendor chart.js 4.5.1 + marked 18.0.5 (provenance in `vendored.md`)
  - [x] html/css/render.js scaffold; report.py copies assets; verified loading in browser
  - [x] mono-ledger visual design system
- [x] `render.js` builds all PRD §8.2 sections from the data files
  - [x] hero + KPI (§8.2.1–2); heatmap + scatter (§8.2.3–4)
  - [x] tables: files/brittle/difficulty/findings/unspecified/prescriptions (§8.2.5–9, §8.2.11)
  - [x] symbol coverage matrix w/ search, filters, expand/collapse, legend, deferred stubs (§8.2.12)
  - [x] agent insights + footer (§8.2.10, §8.2.13)

## Phase 4 — Agent + supporting files
- [x] `SKILL.md`: drive pipeline, scope confirmation, per-symbol analysis (PRD §5–6), `report_content.json`
- [x] `README_template.md` (PRD §10); copied into output by report.py
- [x] `edge_case_taxonomy.md`, `sensitivity_keywords.md`

## Phase 5 — Validation
- [x] End-to-end run on a real repo (nlohmann/json, 958 symbols); all report sections populate, incremental re-run skips unchanged symbols
- [x] Schema validation enforced at every stage boundary
- Validation caught and fixed two real C++ bugs: declarator-chain name extraction and macro-induced parse misnesting.

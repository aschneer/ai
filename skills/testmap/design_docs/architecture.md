# Architecture

How the Testmap skill is **built** — engineering structure and implementation choices. What the product does and the rules it enforces are in `prd.md`. How a user or agent runs it lives in `SKILL.md` and the output-folder `README.md`. This document covers code: the pipeline, the agent/code split, the data files, and the module layout.

The deliverable is an **AI agent skill** (`SKILL.md` + Python libraries + JSON Schema files), not a standalone application.

---

## 1. Design principles

1. **Minimal code, agent for judgment.** Write Python only where correctness requires determinism (parsing, hashing, scoring formulas, tool dispatch, rendering). Everything that is a judgment call — assertion quality, spec inference, behavior enumeration, test-to-cell mapping — is done by the agent and is never coded.
2. **Clean unidirectional pipeline.** Each stage reads zero or more prior stage outputs and writes exactly one new output file. **No stage ever edits a file produced by an earlier stage.** A stage that needs to "add" data to a symbol writes a *new keyed file*, joined to the index by symbol ID downstream.
3. **Modular libraries, thin CLIs.** Logic lives in `*_lib.py`; entry points (`[project.scripts]`) parse args and call into libraries.
4. **Schema-validated JSON.** Every pipeline file has a JSON Schema authored in YAML (`schemas/*.schema.yaml`). Stages validate their input on read and their output on write; a malformed handoff fails fast at the boundary.
5. **Incremental by content hash.** Re-runs recompute only what changed, keyed on body hash and covering-test-file hashes.

---

## 2. Agent vs. deterministic code

The single rule: a capability is **code** only if its output must be identical and correct on every run. Otherwise it is **agent**.

| Capability | Owner | Why |
|------------|-------|-----|
| Symbol discovery (tree-sitter walk) | code | Parsing must be exact and reproducible. |
| Symbol metadata (hashes, complexity count, error-path presence, decorators, visibility) | code | Mechanical extraction from the parse tree. |
| Incremental index merge | code | Hash comparison; must not drift. |
| Staleness detection | code | Pure hash/timestamp comparison. |
| Risk triage scoring + bucketing | code | A fixed formula over fixed signals (PRD 4.1); must be reproducible. |
| Call-site count, git churn | code | grep / `git log`; mechanical. |
| Mutation tool dispatch + result parse | code | Subprocess orchestration; deterministic. |
| Composite score, grade, all report charts/tables | code | Fixed formulas (PRD 8.2.1) and rendering. |
| **Testability rating + note** | **agent** | Judgment over 8 structural signals (PRD 5.2). |
| **Spec inference** | **agent** | Reading intent from code. |
| **Behavior matrix** (input classes × expected behaviors) | **agent** | Requires understanding semantics. |
| **Test-to-cell mapping + assertion-quality / brittleness judgment** | **agent** | The core judgment of the skill. |
| **Cell classification** (covered/gap/unspecified), gap notes, prescriptions | **agent** | Judgment; must not invent contracts. |
| **Narrative summary, agent insights** | **agent** | Prose synthesis. |

The agent's behavioral analysis is not a script. The skill (`SKILL.md`) instructs the agent to, per in-scope symbol, read the body and its covering tests and emit a JSON object conforming to `analysis.schema.yaml`. A small library validates that JSON and assembles the per-symbol objects into `analysis.json`; it does not produce the analysis.

---

## 3. Pipeline

Each box is one stage. Arrows are file dependencies. **No back-edges** — a stage only ever reads upstream files and writes its own.

```
                 ┌─────────────────────────────────────────────┐
 target dir ───▶ │ 1. discover  (code)                         │──▶ index.json
                 └─────────────────────────────────────────────┘
                 ┌─────────────────────────────────────────────┐
 index.json ───▶ │ 2. triage    (code)                         │──▶ triage.json
   git/grep      └─────────────────────────────────────────────┘
                 ┌─────────────────────────────────────────────┐
 index.json  ──▶ │ 3. staleness (code)                         │──▶ scope.json
 triage.json     │    + scope selection (agent asks user)      │   (which symbols
 (prior analysis)└─────────────────────────────────────────────┘    to analyze)
                 ┌─────────────────────────────────────────────┐
 index.json  ──▶ │ 4. analyze   (AGENT, per symbol)            │──▶ analysis.json
 scope.json      │    spec, behavior matrix, test mapping,     │
 source+tests    │    testability rating                       │
                 └─────────────────────────────────────────────┘
                 ┌─────────────────────────────────────────────┐
 scope.json  ──▶ │ 5. mutate    (code, optional)               │──▶ mutation.json
 index.json      │    dispatch per-language mutation tool      │
                 └─────────────────────────────────────────────┘
                 ┌─────────────────────────────────────────────┐
 index.json  ──▶ │ 6. report    (code)                         │──▶ report/report.html
 triage.json     │    join all files by symbol id, render      │   meta.json
 analysis.json   └─────────────────────────────────────────────┘
 mutation.json
 meta.json
```

### Why separate files instead of writing back to `index.json`

The PRD says triage results are "written back to `index.json`" (4.3) and mutation results "written to the symbol's `analysis.json` entry" (7.2). We honor the *intent* (that data is associated per symbol and available to the report) while following the clean-pipeline constraint: **triage writes `triage.json`, mutation writes `mutation.json`**, each keyed by symbol ID. The report stage joins them. This keeps every stage idempotent and independently re-runnable, makes each handoff schema-checkable, and means a failed or re-run stage can never corrupt an upstream file. The report is still "fully regenerable from the output files" (PRD 8.3) — it just reads four files instead of two.

### Joining

Every per-symbol file (`triage.json`, `analysis.json`, `mutation.json`) is a map `symbol_id → record`. `symbol_id` is the stable key minted in stage 1 (qualified name + relative path; see §5). The report stage left-joins all of them onto `index.json`, which is always the complete symbol set (PRD 9.2).

---

## 4. Stage detail

### Stage 1 — `discover` → `index.json`

Walks every source file with tree-sitter (one grammar per supported language, PRD 2.2), extracts each function/method/class, and records all of PRD 2.3. **Incremental:** loads any existing `index.json`, and for each symbol re-emits the existing entry unchanged unless its body hash differs (PRD 2.5). Body hash = SHA-256 of the full node bytes; signature hash = SHA-256 of the signature line. Complexity is a branch-keyword count; error-path presence and decorators/visibility come from the parse tree. The index is the authoritative complete symbol list.

### Stage 2 — `triage` → `triage.json`

Reads `index.json`. For each symbol computes the PRD 4.1 signals — complexity (from index), error-path presence (from index), sensitivity-keyword match (name/path), call-site count (grep), git churn (`git log` over 90 days), no-analysis flag (vs. prior `analysis.json` if present), public-API flag (from index visibility) — combines them into a composite score with a fixed weighting, and buckets into high/medium/low. Writes one record per symbol with bucket, score, and every raw signal value (PRD 4.3). Pure function of its inputs → fully reproducible.

### Stage 3 — `staleness` + scope → `scope.json`

`staleness_lib` compares each symbol's current body hash and covering-test hashes against the prior `analysis.json` to classify each as `no-analysis` / `stale` / `up-to-date` (PRD 3.1). The agent then presents the pre-analysis summary (PRD 4.4), asks the user for scope (all / high-only / custom subset, PRD 4.5), and writes the confirmed symbol-ID list to `scope.json`. `scope.json` is the contract the analyze stage consumes — it makes "what we agreed to analyze" an explicit, inspectable artifact rather than conversational state.

### Stage 4 — `analyze` → `analysis.json` (agent)

The skill drives the agent through each symbol in `scope.json`: infer the one-sentence spec, walk the edge-case taxonomy (`edge-case-taxonomy.md`) to enumerate input classes, enumerate expected behaviors (returns, raises, side effects, negative-space, async — PRD 6.3), build the behavior matrix, grep for and read covering tests, judge each cell covered/gap/unspecified with assertion-quality and brittleness checks, and rate testability. The agent emits, per symbol, a JSON object conforming to `analysis.schema.yaml`. A thin `analysis_lib` validates each object and assembles `analysis.json`. **Incremental:** symbols already up-to-date in the prior `analysis.json` and not in scope are carried forward verbatim; only in-scope symbols are (re)written.

### Stage 5 — `mutate` → `mutation.json` (optional)

Reads `scope.json` + `index.json`. Groups in-scope symbols by file and language, dispatches the per-language mutation tool once per unique file (not per symbol), parses survived/killed/tool/exit-code, and attributes results to each symbol in that file by line-range intersection. Writes one record per symbol to `mutation.json`. Optional and isolated so a missing or failing mutation tool never blocks the report.

### Stage 6 — `report` → `report/report.html` + `meta.json`

Reads `index.json`, `triage.json`, `analysis.json`, and (if present) `mutation.json`. Computes the composite score and grade (PRD 8.2.1), renders the HTML report (all sections of PRD 8.2 — hero, KPI strip, heatmap, scatter, tables, symbol matrix), and writes run metadata to `meta.json` (PRD 9.3). Also copies `README_template.md` → `README.md` (PRD 10). The covered-but-survived discrepancy (PRD 7.3) is computed here by joining `analysis.json` cell status against `mutation.json`. Charts use Chart.js, bundled as a local file in `report/` alongside `report.html` — no external network dependencies (PRD 8.1.2).

---

## 5. Output directory and data files

`<target_dir>/testmap_output/` (PRD 1.2). Committed files at root; ephemeral files (if any) under `temp/` which is gitignored (PRD 1.3).

| File | Producer | Schema | Committed |
|------|----------|--------|-----------|
| `index.json` | discover | `index.schema.yaml` | yes |
| `triage.json` | triage | `triage.schema.yaml` | yes |
| `scope.json` | staleness/scope | `scope.schema.yaml` | yes |
| `analysis.json` | analyze (agent) | `analysis.schema.yaml` | yes |
| `mutation.json` | mutate | `mutation.schema.yaml` | yes |
| `meta.json` | report | `meta.schema.yaml` | yes |
| `report/report.html` | report | — | yes |
| `report/chart.js` | report | — | yes |
| `README.md` | report (copy of template) | — | yes |
| `temp/*` | any | — | no (gitignored) |

`scope.json`, `triage.json`, and `mutation.json` are not named in the PRD's output list (PRD 10.3.2 enumerates only `index`/`analysis`/`report`/`meta`). They are pipeline intermediates required by the clean-pipeline design. **Open question for the user:** keep them at root and committed (so re-runs are incremental across machines), or treat them as ephemeral under `temp/`. Recommendation: keep `triage.json` committed (cheap, useful diff signal) and `scope.json`/`mutation.json` likewise committed for reproducibility; revisit if the PRD's file list is meant to be exhaustive.

### Symbol ID

The join key across all files. Deterministic: `"{relative_path}::{qualified_name}::{start_line}"` is too brittle (line shifts break it); instead use `"{relative_path}::{qualified_name}"`, with overload/collision disambiguated by an index-assigned ordinal suffix. Minted in stage 1, stored in `index.json`, referenced everywhere downstream.

### Schemas

JSON Schema authored in YAML, validated in-editor (Red Hat YAML) and at runtime via `jsonschema` — same approach as the schedule skill. Each pipeline file gets a schema; the agent's `analysis.json` output is validated against `analysis.schema.yaml` on assembly, which is the safety net that lets us trust agent-produced JSON.

---

## 6. Module layout (UV project)

Organized as a UV project rooted at the skill directory, mirroring the schedule skill (`src/<pkg>` layout, `[project.scripts]` entry points, committed `uv.lock`).

```
skills/testmap/
  SKILL.md
  README_template.md            # copied verbatim into each output folder (PRD 10.2)
  edge_case_taxonomy.md         # agent checklist for input-class enumeration
  sensitivity_keywords.md       # categorized keywords for triage signal 4.1.3
  pyproject.toml
  uv.lock
  .gitignore                    # ignores testmap_output/temp/, .venv, __pycache__
  design_docs/
    prd.md
    architecture.md
    decisions.md                # ADRs (created when first decision logged)
  schemas/
    index.schema.yaml
    triage.schema.yaml
    scope.schema.yaml
    analysis.schema.yaml
    mutation.schema.yaml
    meta.schema.yaml
  src/testmap/
    discover.py                 # CLI: stage 1
    triage.py                   # CLI: stage 2
    staleness.py                # CLI: stage 3 (staleness compute; scope written by agent)
    mutate.py                   # CLI: stage 5
    report.py                   # CLI: stage 6
    analysis_cli.py             # CLI: agent interface to analysis.json (read/write/list/summary)
    discover_lib.py             # tree-sitter walk, symbol extraction, hashing
    languages_lib.py            # language → grammar + node-kind mapping, mutation-tool map
    index_lib.py                # incremental merge, symbol id, load/save index.json
    triage_lib.py               # signal collection + scoring + bucketing
    churn_lib.py                # git churn + call-site count helpers
    staleness_lib.py            # hash/timestamp comparison
    analysis_lib.py             # validate + assemble agent-produced analysis.json
    mutation_lib.py             # per-language tool dispatch + result parse
    report_lib.py               # join, composite score, HTML/SVG render
    schema_lib.py               # shared: load schema, validate, read/write JSON
    paths_lib.py                # output-dir path resolution
    assets/                     # report HTML template, CSS (inlined at render)
  tests/
    fixtures/                   # small multi-language sample repos
    test_*.py
  evals/                        # agent-stage evals (analysis quality)
```

There is no `analyze.py` CLI — stage 4 is agent-driven. `analysis_lib.py` exists only to validate and assemble what the agent writes.

### `[project.scripts]`

```
discover      = "testmap.discover:main"
triage        = "testmap.triage:main"
staleness     = "testmap.staleness:main"
mutate        = "testmap.mutate:main"
report        = "testmap.report:main"
analysis-cli  = "testmap.analysis_cli:main"
```

Run as `uv run discover <target_dir>`, etc.

---

## 7. Dependencies

- `tree-sitter` + per-language grammar packages (`tree-sitter-python`, `tree-sitter-javascript`, … for the 15 languages in PRD 2.2). **Open question:** these are heavy; confirm bundling all 15 vs. lazy-installing the grammar for languages actually present in the target. Recommendation: lazy — `languages_lib` installs/loads only grammars for detected file extensions.
- `jsonschema` — schema validation.
- `pyyaml` — read schemas (authored in YAML).
- Mutation tools (mutmut, Stryker, PIT, …) are **not** Python deps — they are external per-language tools dispatched by subprocess and assumed present in the target's toolchain; absence is handled gracefully (stage 5 records the failure and the report omits mutation data).
- dev: `pytest`.

---

## 8. Error handling and validation

- Every stage validates its input files against their schemas on read and its output against its schema on write. A schema failure aborts that stage with a clear message naming the file and the violated constraint — bad handoffs never silently propagate.
- The agent stage's output is the one non-code-generated input; `analysis_lib` validating it against `analysis.schema.yaml` is the boundary that keeps malformed agent JSON out of the report.
- Mutation and git operations are best-effort: failures are recorded, not fatal.
- The pre-analysis summary includes a notice that output will be written to `testmap_output/` and existing files overwritten; the user should commit before proceeding (PRD 4.4.4).

---

## 9. Design decisions

See `decisions.md` for all design decisions and rationale.

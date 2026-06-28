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
| Git churn | code | `git log`; mechanical. |
| Mutation tool dispatch + result parse | code | Subprocess orchestration; deterministic. |
| Composite score + grade | code | Fixed formula (PRD 8.2.1); must be reproducible. |
| **Testability rating + note** | **agent** | Judgment over 8 structural signals (PRD 5.2). |
| **Spec inference** | **agent** | Reading intent from code. |
| **Behavior matrix** (input classes × expected behaviors) | **agent** | Requires understanding semantics. |
| **Test-to-cell mapping + assertion-quality / brittleness judgment** | **agent** | The core judgment of the skill. |
| **Cell classification** (covered/gap/unspecified), gap notes, prescriptions | **agent** | Judgment; must not invent contracts. |
| **Narrative summary + agent insights** | **agent** | Written in markdown to `report_content.json`; rendered by `render.js` at page load. |

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
 index.json  ──▶ │ 6. report    (code + agent)                 │──▶ meta.json
 triage.json     │    code: composite score, meta.json         │   report_content.json
 analysis.json   │    agent: narrative + insights              │   report/ (static assets)
 mutation.json   └─────────────────────────────────────────────┘
```

### Why separate files instead of writing back to `index.json`

Triage writes `triage.json`; mutation writes `mutation.json` — neither writes back to an upstream file. The report stage joins all files by symbol ID. This keeps every stage idempotent and independently re-runnable, makes each handoff schema-checkable, and means a failed or re-run stage can never corrupt an upstream file. The report is fully regenerable from the pipeline output files (PRD 8.3).

### Joining

Every per-symbol file (`triage.json`, `analysis.json`, `mutation.json`) is a map `symbol_id → record`. `symbol_id` is the stable key minted in stage 1 (qualified name + relative path; see §5). The report stage left-joins all of them onto `index.json`, which is always the complete symbol set (PRD 9.2).

---

## 4. Stage detail

### Stage 1 — `discover` → `index.json`

Walks every source file with tree-sitter (one grammar per supported language, PRD 2.2), extracts each function/method/class, and records all of PRD 2.3. **Incremental:** loads any existing `index.json`, and for each symbol re-emits the existing entry unchanged unless its body hash differs (PRD 2.5). Body hash = SHA-256 of the full node bytes; signature hash = SHA-256 of the signature line. Complexity is a branch-keyword count; error-path presence and decorators/visibility come from the parse tree. The index is the authoritative complete symbol list.

### Stage 2 — `triage` → `triage.json`

Reads `index.json`. For each symbol computes the PRD 4.1 signals — complexity (from index), error-path presence (from index), sensitivity-keyword match (name/path), git churn (`git log` over 90 days), no-analysis flag (vs. prior `analysis.json` if present), public-API flag (from index visibility) — combines them into a composite score with a fixed weighting, and buckets into high/medium/low. Writes one record per symbol with bucket, score, and every raw signal value (PRD 4.3). Pure function of its inputs → fully reproducible.

### Stage 3 — `staleness` + scope → `scope.json`

`staleness_lib` compares each symbol's current body hash and covering-test hashes against the prior `analysis.json` to classify each as `no-analysis` / `stale` / `up-to-date` (PRD 3.1). The agent then presents the pre-analysis summary (PRD 4.4), asks the user for scope (all / high-only / custom subset, PRD 4.5), and writes the confirmed symbol-ID list to `scope.json`. `scope.json` is the contract the analyze stage consumes — it makes "what we agreed to analyze" an explicit, inspectable artifact rather than conversational state.

### Stage 4 — `analyze` → `analysis.json` (agent)

The skill drives the agent through each symbol in `scope.json`: infer the one-sentence spec, walk the edge-case taxonomy (`edge_case_taxonomy.md`) to enumerate input classes, enumerate expected behaviors (returns, raises, side effects, negative-space, async — PRD 6.3), build the behavior matrix, grep for and read covering tests, judge each cell covered/gap/unspecified with assertion-quality and brittleness checks, and rate testability. The agent emits, per symbol, a JSON object conforming to `analysis.schema.yaml`. A thin `analysis_lib` validates each object and assembles `analysis.json`. **Incremental:** symbols already up-to-date in the prior `analysis.json` and not in scope are carried forward verbatim; only in-scope symbols are (re)written.

### Stage 5 — `mutate` → `mutation.json` (optional)

Reads `scope.json` + `index.json`. Groups in-scope symbols by file and language, dispatches the per-language mutation tool once per unique file (not per symbol), parses survived/killed/tool/exit-code, and attributes results to each symbol in that file by line-range intersection. Writes one record per symbol to `mutation.json`. Optional and isolated so a missing or failing mutation tool never blocks the report.

### Stage 6 — `report` → `report/` + `meta.json`

Two sub-steps:

1. **Code:** Computes composite score and grade (PRD 8.2.1) from `analysis.json` + `triage.json`. Writes `meta.json` (PRD 9.3). Copies `README_template.md` → `README.md` (PRD 10).

2. **Agent:** Writes `report_content.json` — narrative summary and agent insights in markdown. This is the only file the agent writes in this stage. Agent then prints the local server start command (e.g. `python3 -m http.server 8080` from `testmap_output/`).

`report/report.html`, `report/render.js`, `report/chart.js`, and `report/marked.js` are static assets shipped with the skill and copied into `report/` on each run — never regenerated at runtime. `render.js` fetches `../index.json`, `../triage.json`, `../analysis.json`, `../report_content.json`, and (if present) `../mutation.json` at page load and renders all sections.

---

## 5. Output directory and data files

`<target_dir>/testmap_output/` (PRD 1.2). Committed files at root; ephemeral files (if any) under `temp/` which is gitignored (PRD 1.3).

| File | Producer | Schema | Committed |
|------|----------|--------|-----------|
| `index.json` | discover | `index.schema.yaml` | yes |
| `triage.json` | triage | `triage.schema.yaml` | yes |
| `analysis.json` | analyze (agent) | `analysis.schema.yaml` | yes |
| `mutation.json` | mutate | `mutation.schema.yaml` | yes (if present) |
| `meta.json` | report (code) | `meta.schema.yaml` | yes |
| `report_content.json` | report (agent) | `report_content.schema.yaml` | yes |
| `README.md` | report (copy of template) | — | yes |
| `report/report.html` | static skill asset | — | yes |
| `report/render.js` | static skill asset | — | yes |
| `report/chart.js` | static skill asset | — | yes |
| `report/marked.js` | static skill asset | — | yes |
| `temp/scope.json` | staleness/scope | `scope.schema.yaml` | no (gitignored) |
| `temp/*` | any | — | no (gitignored) |

`scope.json` is ephemeral (temp/); all other files at root are committed. See `decisions.md` for rationale.

### Symbol ID

The join key across all files. Deterministic: `"{relative_path}::{qualified_name}::{normalized_signature}"`, where `normalized_signature` is the symbol's signature line with all whitespace stripped. Minted in stage 1, stored in `index.json`, referenced everywhere downstream.

Including line numbers (`::{start_line}`) is too brittle — editing code above a symbol shifts its line and breaks the key with no semantic change. The normalized signature is appended uniformly to every key, not only on collision: it is the only component that distinguishes overloads (same path + same qualified name, different parameters), and a uniform rule avoids a collision-detection branch and keeps keys predictable. The signature is already extracted during discovery (PRD 2.3.6), so this adds no parsing work. Trade-off: reformatting a signature (e.g. renaming a parameter) changes the key, making the symbol look new on the next run — rare, and arguably correct, since a changed signature is a changed contract.

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
    report_content.schema.yaml
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
    churn_lib.py                # git churn helpers
    staleness_lib.py            # hash/timestamp comparison
    analysis_lib.py             # validate + assemble agent-produced analysis.json
    mutation_lib.py             # per-language tool dispatch + result parse
    report_lib.py               # composite score + grade formula, meta.json assembly
    schema_lib.py               # shared: load schema, validate, read/write JSON
    paths_lib.py                # output-dir path resolution
    assets/                     # static report assets: report.html, render.js, chart.js, marked.js
  tests/
    fixtures/                   # small multi-language sample repos
    test_*.py
  evals/                        # agent-stage evals (analysis quality)
```

There is no `analyze.py` CLI — stage 4 is agent-driven. `analysis_lib.py` exists only to validate and assemble what the agent writes.

### `analysis_cli.py` — agent interface to `analysis.json` (PRD 11)

The entry-at-a-time access required by PRD 11.1 is provided by `analysis_cli.py`. All commands take the path to the `analysis.json` file directly as the first argument:

| Command | Behavior |
|---------|----------|
| `read <analysis_json> <symbol_key>` | Print one symbol's analysis entry as JSON to stdout. |
| `write <analysis_json> <symbol_key> <json>` | Update one symbol's entry; create the file if absent. |
| `list-keys <analysis_json>` | Print all symbol keys, one per line. |
| `list-stale <analysis_json>` | Print keys of all symbols whose analysis is stale or missing. |
| `summary <analysis_json>` | Print a JSON count summary (total, analyzed, stale, by priority bucket) without loading full entries. |

Symbol keys are the symbol IDs minted in stage 1 (see §5). All commands exit 0 on success, non-zero on error with a human-readable message to stderr.

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

- `tree-sitter` + `tree-sitter-language-pack` — the language pack bundles all supported grammars in one dependency. `languages_lib` loads a grammar lazily (`get_parser(lang)`) only for languages whose file extensions are detected in the target directory. (Chosen over 15 separate per-language grammar packages: one dep and no per-extension install logic, at the cost of carrying all grammars on disk. See `decisions.md`.)
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

# Testmap — Design Decisions

Most recent first.

---

## 2026-06-28 23:10:00 UTC — Symbol kind (function vs method) inferred from ancestor context, not node type

**What:** Discovery classifies a symbol as `method` vs `function` by its position in the tree — a function-like node whose ancestor chain includes a class/impl/interface body is a `method`; otherwise a `function`. `languages_lib` stores per-language *function-like* node kinds and *class-like* node kinds only; it does not store a separate "method" node kind.

**Why:** Probing all 15 grammars (`tree-sitter-language-pack`) showed most do not have a distinct method node — a method is the same node kind as a free function (e.g. `function_definition` in Python/PHP/C++, `function_declaration` in Kotlin/Swift, `function_item` in Rust), differing only by being nested in a class/impl body. The few that do differ (JS/TS `method_definition`, Go/Java/C# `method_declaration`, Ruby `method`) are handled by also listing those kinds as function-like and letting the same ancestor rule label them. One context rule is simpler and more uniform than a per-language method-kind table.

**Trade-offs:** Requires tracking ancestry during the walk (cheap — the cursor already descends through class bodies). Nested functions (a `def` inside a `def`) are still `function`, not `method`, since no class ancestor — correct.

**Binding note:** `tree-sitter-language-pack` exposes a Rust-backed binding where node accessors are methods, not properties (`node().kind()`, `node().child_count()`, `node().byte_range()`), and traversal is via the `.walk()` cursor (`goto_first_child` / `goto_next_sibling` / `goto_parent`). Discovery code uses the cursor, not a `children` property.

---

## 2026-06-28 22:15:00 UTC — Use tree-sitter-language-pack instead of per-language grammar packages

**What:** One dependency (`tree-sitter-language-pack`) bundles all supported grammars. `languages_lib` still loads lazily — only grammars for extensions present in the target are parsed via `get_parser(lang)`. Refines the earlier "grammars lazy-loaded" decision (2026-06-28 17:52:00 UTC), which assumed separate per-language packages installed on demand.

**Why:** Installing/managing 15 separate grammar packages needs an extension→package map plus runtime install logic (network at analysis time, failure handling). The language pack gives every grammar in one pinned dep with no install step; lazy `get_parser` keeps the runtime-load benefit.

**Trade-offs:** Carries all grammars on disk even when the target uses one language — a few MB, paid once at install. Acceptable vs. the code and runtime-install complexity avoided. Runtime parsing stays lazy, so unused grammars are never loaded into memory.

**What:** The symbol-ID join key is `relative_path::qualified_name::normalized_signature`, where `normalized_signature` is the signature line with all whitespace removed. The signature component is appended to every key uniformly, not only when a name collision exists. Supersedes the ordinal-suffix scheme (2026-06-28 17:53:00 UTC).

**Why:** The ordinal suffix (`::0`, `::1`) is not stable: inserting or reordering an overload shifts ordinals and breaks the join keys of every overload below it — the same line-number fragility line-exclusion was meant to avoid. The signature is the actual differentiator between overloads (same path + qualified name, different parameters) and is invariant under reordering. It is already extracted at discovery (PRD 2.3.6), so no extra parsing.

**Trade-offs:** Applying the signature uniformly (vs. only on collision) makes the common non-overloaded key longer/noisier, but removes a collision-detection branch and keeps the key format predictable — chosen for simplicity. Reformatting a signature (e.g. a parameter rename) changes the key, so the symbol reads as new on the next run; rare, and arguably correct since a changed signature is a changed contract.

---

## 2026-06-28 20:06:00 UTC — report/ contains only static rendering assets; all data at root

**What:** `report/` holds only static skill assets (`report.html`, `render.js`, `chart.js`, `marked.js`). All data files (`index.json`, `triage.json`, `analysis.json`, `mutation.json`, `meta.json`, `report_content.json`) live at the root of `testmap_output/`. `report/` can be deleted and regenerated without data loss.

**Why:** Clean separation between data (root, committed, authoritative) and rendering layer (report/, regenerable). `render.js` fetches data as `../filename` — consistent one-level-up path for all data files.

---

## 2026-06-28 20:05:00 UTC — Agent insights and narrative summary stored as markdown in report_content.json

**What:** Agent writes `report_content.json` at the root of `testmap_output/` each run. Contains `narrative_summary` (markdown string) and `insights` (array of `{title, body}` markdown objects). `render.js` fetches and renders them via `marked.js` at page load.

**Why:** Keeps agent-written content in a data file separate from the static rendering layer. Agent never touches HTML. Markdown is the right format — agent writes it naturally, `marked.js` handles rendering.

---

## 2026-06-28 19:47:00 UTC — Report is a browser app; data loaded via fetch() at render time

**What:** `render.js` fetches pipeline JSON files (`../index.json`, `../triage.json`, `../analysis.json`, `../mutation.json`) at page load. Data is never embedded in the HTML. Report requires a local web server to view. Agent prints the server start command at the end of the run.

**Why:** Embedding data in HTML requires the agent to read potentially megabytes of JSON into context and re-emit it — expensive tokens for pure mechanical string injection. fetch() keeps data files as the source of truth and the agent out of the data path entirely.

---

## 2026-06-28 19:46:00 UTC — Report HTML and render.js generated by agent, not code

**What:** Agent generates `report/report.html` and `report/render.js`. Code only computes the composite score/grade and writes `meta.json`. No Python HTML templating library.

**Why:** A Python rendering layer for the full report would be hundreds of lines of brittle templating code. Agent generates it more flexibly with less code and is easier to iterate on — change the prompt, not a template.

---

## 2026-06-28 19:45:00 UTC — Call-site count signal dropped from triage

**What:** Call-site count (grep-based) removed from triage signals. Six signals remain: cyclomatic complexity, error-path presence, sensitivity keyword match, git churn, no-analysis flag, public API flag.

**Why:** Triage is directional, not precise — six signals is sufficient. Call-site count added grep I/O and name-disambiguation complexity for marginal gain. Other signals (sensitivity keywords, public API flag) already capture the "widely depended on" dimension adequately.

---

## 2026-06-28 18:00:00 UTC — scope.json is ephemeral

**What:** `scope.json` lives under `temp/` and is not committed.

**Why:** Fully reproducible from `index.json` + `triage.json` + user intent. No value after the run; committing it creates noisy diffs.

---

## 2026-06-28 17:59:00 UTC — Clean unidirectional pipeline; no stage edits upstream output

**What:** Each stage writes its own output file; no stage edits a file produced by an earlier stage. Triage writes `triage.json` (not back to `index.json`); mutation writes `mutation.json` (not into `analysis.json`). Report stage joins all files by symbol ID.

**Why:** Keeps every stage idempotent and independently re-runnable. Each handoff is schema-checkable. A failed or re-run stage cannot corrupt upstream files.

---

## 2026-06-28 17:58:00 UTC — analysis_cli.py: agent reads/writes analysis.json one entry at a time

**What:** A composable CLI (`analysis_cli.py`) lets the agent read, write, list, and summarize `analysis.json` entries without loading the full file into context.

**Why:** `analysis.json` can be several MB for large codebases. Loading it whole on every per-symbol write is expensive. The CLI keeps only one entry in context at a time.

---

## 2026-06-28 17:57:00 UTC — Overwrite warning folded into pre-analysis summary

**What:** No separate confirmation gate before overwriting `testmap_output/`. Instead, the pre-analysis summary (§4.4.4) includes a notice that output will be written and existing files overwritten; user should commit first.

**Why:** A dedicated gate trains users to click through it mindlessly. Folding it into the summary they already read is less friction with the same information.

---

## 2026-06-28 17:56:00 UTC — Report is a folder, not a single file

**What:** Report output is `report/report.html` + `report/chart.js`. No self-contained single-file requirement.

**Why:** Inlining Chart.js (~200KB) into every report adds bloat for no benefit. A local folder with no external network dependencies satisfies the portability requirement cleanly.

---

## 2026-06-28 17:55:00 UTC — Mutation testing is opt-in per run

**What:** Mutation testing does not run automatically. User must explicitly request it.

**Why:** Mutation tools are slow (10–30 min on medium codebases). Auto-running them would make the skill unusably slow for large codebases.

---

## 2026-06-28 17:54:00 UTC — Missing mutation tool flagged explicitly in report

**What:** For languages with no supported mutation tool (TSX, Kotlin, C, C++, Swift, Scala), the report explicitly states "mutation testing not available for this language" rather than silently omitting the section.

**Why:** Silent omission implies mutation testing ran and passed. Explicit flagging is honest and sets correct expectations.

---

## 2026-06-28 17:53:00 UTC — ~~Symbol ID: relative_path::qualified_name (+ordinal)~~ (superseded)

Superseded by 2026-06-28 21:30:00 UTC — ordinal suffix replaced by normalized signature (ordinals are not stable under overload reordering).

**What:** Join key across all pipeline files is `relative_path::qualified_name`, with an ordinal suffix to disambiguate overloads. Line numbers excluded.

**Why:** Line numbers change when code above a symbol is edited, invalidating join keys without any semantic change to the symbol itself.

---

## 2026-06-28 17:52:00 UTC — Tree-sitter grammars lazy-loaded

Refined by 2026-06-28 22:15:00 UTC — grammars now come from `tree-sitter-language-pack` (one dep, no per-language install); runtime loading stays lazy.

**What:** `languages_lib` installs and loads only grammars for file extensions detected in the target directory.

**Why:** Bundling all 15 grammars unconditionally adds install time and disk weight for languages not present in the target.

---

## 2026-06-28 17:51:00 UTC — Test file detection by agent inference, not hardcoded globs

**What:** Agent infers test file conventions from repo structure (naming patterns, directory names). No hardcoded glob list shipped with the skill. `testmap_config.json` does not expose a `test_patterns` override.

**Why:** A capable agent can detect conventions contextually. A hardcoded list adds maintenance burden and is frequently wrong for non-standard layouts.

---

## 2026-06-29 00:05:00 UTC — Sensitivity matching is mechanical code, not agent judgment

**What:** Amends 2026-06-28 17:50:00 UTC. Triage signal 4.1.3 is computed by the triage stage (code): it parses the backticked keywords out of `sensitivity_keywords.md` and word/substring-matches them against each symbol's name and file path. The agent does not judge sensitivity. `sensitivity_keywords.md` keeps its categories and risk rationale — they document intent for human readers and let the keyword list be maintained thoughtfully — but the matching itself is deterministic.

**Why:** Triage must be a reproducible pure function of its inputs (architecture §2, §4) so `triage.json` is stable across runs and triage needs no agent pass before scope confirmation. Triage is directional, not precise (decision 2026-06-28 19:45), so the marginal precision from agent-judged borderline matches does not justify making one of six signals non-reproducible and inserting an extra agent step. Word/substring matching catches the common cases (`auth` matches `authenticate`).

**Trade-offs:** Loses nuanced judgment on partial-word and out-of-list matches. Acceptable for a directional signal; the keyword list can be extended if recall is poor.

---

## 2026-06-28 17:50:00 UTC — ~~Sensitivity keywords in annotated markdown file~~ (amended)

Amended by 2026-06-29 00:05:00 UTC — the agent no longer matches sensitivity; matching is mechanical code over the same file.

**What:** Security/correctness sensitivity keywords for triage signal 4.1.3 live in `sensitivity_keywords.md`, categorized with risk rationale. Agent reads this file at triage time.

**Why:** Categories and rationale let the agent judge borderline and partial-word matches rather than doing blind keyword lookup. Separate from the edge-case taxonomy — different purpose.

---

## 2026-06-28 17:49:00 UTC — ~~Call-site count via scoped grep with confidence flag~~ (superseded)

Superseded by 2026-06-28 19:45:00 UTC — call-site count dropped entirely.

---

## 2026-06-28 17:48:00 UTC — Git churn skipped gracefully if not a git repo

**What:** If the target directory is not a git repository, the churn signal (4.1.5) is omitted. The pre-analysis summary logs a warning. Score computed from remaining signals.

**Why:** Churn is one of seven signals. Failing the whole run over a missing signal is disproportionate.

---

## 2026-06-28 17:47:00 UTC — "Untestable" folds into "unspecified"

**What:** No fourth cell status. Cells that are genuinely impossible to test are classified `unspecified`; the unspecified reason field explains why.

**Why:** Both statuses require human decision before action. A fourth status adds schema, rendering, and scoring complexity for a rare edge case.

---

## 2026-06-28 17:46:00 UTC — Trivial class threshold: all methods cyclomatic complexity ≤ 1, no error paths

**What:** A class qualifies as trivial (PRD §6.4.5) if all its methods combined have cyclomatic complexity ≤ 1 and no error paths.

**Why:** Captures pure data holders (dataclasses, DTOs, structs) while excluding anything with real conditional logic. Uses already-computed values from symbol discovery — no extra analysis.

---

## 2026-06-28 17:45:00 UTC — Per-symbol writes to analysis.json

**What:** Agent writes each symbol's analysis entry to `analysis.json` immediately after analyzing that symbol, not at end of run.

**Why:** Analysis phase can run 30+ minutes. Per-symbol writes mean a crash loses at most one symbol's work. On resume, incremental logic skips already-analyzed symbols via body hash comparison.

**Trade-offs:** `analysis.json` is partially written mid-run. Acceptable — only consumed by the report step, which runs after analysis completes.

# Testmap — Design Decisions

Most recent first.

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

## 2026-06-28 17:53:00 UTC — Symbol ID: relative_path::qualified_name (+ordinal)

**What:** Join key across all pipeline files is `relative_path::qualified_name`, with an ordinal suffix to disambiguate overloads. Line numbers excluded.

**Why:** Line numbers change when code above a symbol is edited, invalidating join keys without any semantic change to the symbol itself.

---

## 2026-06-28 17:52:00 UTC — Tree-sitter grammars lazy-loaded

**What:** `languages_lib` installs and loads only grammars for file extensions detected in the target directory.

**Why:** Bundling all 15 grammars unconditionally adds install time and disk weight for languages not present in the target.

---

## 2026-06-28 17:51:00 UTC — Test file detection by agent inference, not hardcoded globs

**What:** Agent infers test file conventions from repo structure (naming patterns, directory names). No hardcoded glob list shipped with the skill. `testmap_config.json` does not expose a `test_patterns` override.

**Why:** A capable agent can detect conventions contextually. A hardcoded list adds maintenance burden and is frequently wrong for non-standard layouts.

---

## 2026-06-28 17:50:00 UTC — Sensitivity keywords in annotated markdown file

**What:** Security/correctness sensitivity keywords for triage signal 4.1.3 live in `sensitivity_keywords.md`, categorized with risk rationale. Agent reads this file at triage time.

**Why:** Categories and rationale let the agent judge borderline and partial-word matches rather than doing blind keyword lookup. Separate from the edge-case taxonomy — different purpose.

---

## 2026-06-28 17:49:00 UTC — Call-site count via scoped grep with confidence flag

**What:** Call-site count (triage signal 4.1.4) uses grep scoped by qualified name where possible (e.g., `\.parse\b` for methods). Common/ambiguous names are flagged low-confidence and weighted down in the composite score.

**Why:** A full language server (LSP) for accurate call graphs across 15 languages is prohibitive complexity. Grep with scoping heuristics is good enough for a relative triage signal.

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

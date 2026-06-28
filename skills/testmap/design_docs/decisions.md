# Testmap — Design Decisions

---

## 2026-06-28 — Per-symbol writes to analysis.json

**What:** Agent writes each symbol's analysis entry to `analysis.json` immediately after analyzing that symbol, not at end of run.

**Why:** Analysis phase can run 30+ minutes on large codebases. Per-symbol writes mean a crash or interruption loses at most one symbol's work. On resume, §9.1 incremental logic skips already-analyzed symbols via body hash comparison.

**Trade-offs:** Slightly more I/O; `analysis.json` is in a partially-written state mid-run. Acceptable — the file is only consumed by the report step, which runs after analysis completes.

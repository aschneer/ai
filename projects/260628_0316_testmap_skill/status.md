# Testmap — Status

**Status:** Complete.

## Current state

The skill is fully built, validated, and tested. The pipeline (discover →
triage → staleness/scope → agent analysis → report) runs end-to-end; the
browser report renders all sections; `serve.sh` gives one-command viewing.
Validated on a real codebase (nlohmann/json, 958 symbols) and covered by a
119-test pytest suite. Mutation testing is intentionally deferred (PRD D.2).

Phase-by-phase status: `plan.md`.

## Where things live

| What | Where |
|------|-------|
| Skill source | `skills/testmap/` |
| Design docs (PRD, architecture, decisions) | `skills/testmap/design_docs/` |
| Implementation plan + status | `projects/260628_0316_testmap_skill/` |

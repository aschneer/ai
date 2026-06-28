# Testmap — Status

**Status:** Not started  
**PRD:** `skills/testmap/design_docs/prd.md`

## Current state

PRD is complete and reviewed. No implementation has begun.

## Next steps

1. Write architecture doc (`skills/testmap/design_docs/architecture.md`) — component breakdown, data flow, script responsibilities, agent step boundaries
2. Define JSON schemas for all output files (`index.json`, `analysis.json`, `meta.json`)
3. Rewrite `scripts/build_index.py` per new PRD (new symbol fields: decorators, visibility, is-test-file; output dir changed to `testmap_output/`)
4. Rewrite `scripts/triage.py` per new PRD (new signals: no-analysis flag, visibility; raw signal values written to index)
5. Rewrite `scripts/find_stale.py` per new PRD
6. Update `SKILL.md` agent instructions to match new PRD (new analysis flow: pre-analysis summary, user confirmation, testability analysis, expanded behavioral analysis)
7. Implement `scripts/report.py` — HTML report with all sections defined in PRD §8
8. Write `README_template.md` (static, copied into every `testmap_output/`)
9. End-to-end test on a real codebase

## Where things live

| What | Where |
|------|--------|
| Skill source | `skills/testmap/` |
| PRD | `skills/testmap/design_docs/prd.md` |
| Design docs (planned) | `skills/testmap/design_docs/` |
| Project tracking | `projects/260628_0316_testmap_skill/` |

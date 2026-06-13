# Schedule examples

User-facing demo projects live here. Regression test fixtures are under `tests/fixtures/` — not examples.

## Try the demos

**Simple intro schedule** (~17 tasks):

```bash
cd skills/schedule
uv run validate examples/farmers_market/schedule.yaml
uv run compute examples/farmers_market/schedule.yaml
```

**Full-season stress-test schedule** (~150 tasks, May–October):

```bash
uv run validate examples/farmers_market_full/schedule.yaml
uv run compute examples/farmers_market_full/schedule.yaml
```

Open the Gantt URL printed by `compute`.

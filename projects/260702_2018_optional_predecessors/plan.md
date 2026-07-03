# Optional Predecessors — Implementation Plan

Ordered task list. Design rules live in the schedule skill docs
(`skills/schedule/context/{prd,data_model}.md`, `SKILL.md`) and are updated as
part of this work. This doc tracks order and status only.

Status: `[ ]` todo · `[~]` in progress · `[x]` done

## Goal

Let self-anchoring items omit predecessors:

- Pinned tasks (`start_duration`, `start_finish`, `finish_duration`) — predecessors **optional**.
- Groups — predecessors **optional** (dates roll up from children; a present pred still floors children).
- `auto` tasks — predecessors **still required** (duration-only, needs an anchor).

An item with no predecessors draws no dependency arrow (falls out for free — the
viewer only draws arrows from `item.predecessors`). No compute or viewer code change.

## Decisions locked (from interview)

- Auto tasks + ... keep requiring ≥1 predecessor; pinned tasks and groups do not.
- Group predecessor optional; if present, it floors children (min start / max finish
  by link type). A group pred conflicting with an earlier child pin stays a hard error
  (`validate_pinned_task_bounds`, unchanged).
- Project finish stays the simple max finish across all scheduled items (floaters may
  push it; user reads their real terminal task). No change.
- Critical path unchanged. Lone-critical floater (a no-pred pinned task that happens to
  hold the max finish) is **accepted** — no guard code.
- Milestone 0 stays the required project anchor.

## Phase 1 — Schema + logic
- [ ] `schemas/schedule.schema.yaml`: add `$defs/predecessors_optional` (`minItems: 0`).
- [ ] Point `task_start_duration`, `task_start_finish`, `task_finish_duration`, `group`
      `predecessors` property → `predecessors_optional`; drop `predecessors` from each
      `required` list.
- [ ] `task_auto` unchanged (predecessors required, `minItems: 1`).
- [ ] `logic_validate_lib.py`: verify only — empty preds already skip listing rules
      (`_check_predecessor_listing` early-returns on `not links`). No change expected.

## Phase 2 — Compute (verify, no change expected)
- [ ] Confirm pinned schedulers pin from own fields with no preds.
- [ ] Confirm group with no pred rolls up from children (`_group_anchor_start` → None floor).
- [ ] Confirm group pred still floors children.
- [ ] Confirm auto with no pred + no parent floor stays unscheduled (unreachable via schema
      since auto still requires a pred).

## Phase 3 — Tests
- [ ] Pinned task, no preds → valid, schedules from pin.
- [ ] Group, no preds → valid, rolls up from children.
- [ ] Auto, no preds → schema-rejected.
- [ ] Group pred still floors children (regression).
- [ ] Existing 46 tests pass.

## Phase 4 — Docs
- [ ] `data_model.md`: field table, listing-rules table (add self-anchored pinned row),
      timing table (pinned preds required→optional), group section.
- [ ] `prd.md`: predecessor paragraph (tasks *may* carry preds; required only for auto),
      new DM13 (self-anchoring items need no dependency), viewer note (no pred = no arrow).
- [ ] `SKILL.md`: listing-rule bullets — pinned/group preds optional; auto still needs one.
- [ ] `README.md`: touch only if it restates pred rules.

## Phase 5 — Example + manual check
- [ ] Add a small no-pred availability group (`start_finish` floaters) to
      `examples/farmers_market_full/schedule.yaml`.
- [ ] `uv run compute` → clean; confirm floaters have correct dates and draw no arrows.

## Phase 6 — Review
- [ ] Stop before committing. User reviews all changes.

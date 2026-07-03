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
- [x] `schemas/schedule.schema.yaml`: add `$defs/predecessors_optional` (`minItems: 0`).
- [x] Point `task_start_duration`, `task_start_finish`, `task_finish_duration`, `group`
      `predecessors` property → `predecessors_optional`; drop `predecessors` from each
      `required` list.
- [x] `task_auto` unchanged (predecessors required, `minItems: 1`).
- [x] `logic_validate_lib.py`: verified — empty preds already skip listing rules
      (`_check_predecessor_listing` early-returns on `not links`). No change made.

## Phase 2 — Compute (verify, no change expected)
- [x] Confirmed pinned schedulers pin from own fields with no preds.
- [x] Confirmed group with no pred rolls up from children (`_group_anchor_start` → None floor).
- [x] Confirmed group pred still floors children.
- [x] Confirmed auto with no pred + no parent floor stays unscheduled (unreachable via schema
      since auto still requires a pred). No compute change made.

## Phase 3 — Tests
- [x] Pinned task, no preds → valid, schedules from pin.
- [x] Group, no preds → valid, rolls up from children.
- [x] Auto, no preds → schema-rejected.
- [x] Group pred still floors children (regression).
- [x] Existing tests pass (46 → 53 with new).
- [x] Lone-critical floater edge asserted explicitly (accepted decision).

## Phase 4 — Docs
- [x] `data_model.md`: field table, listing-rules table (self-anchored row),
      timing table (pinned preds required→optional), group section.
- [x] `prd.md`: predecessor paragraph, new DM15 (self-anchoring items need no
      dependency), R9 viewer note (no pred = no arrow).
- [x] `SKILL.md`: kinds table + listing-rule bullets — pinned/group preds optional; auto still needs one.
- [x] `README.md`: no pred rules stated — untouched.

## Phase 5 — Example + manual check
- [ ] Add a small no-pred availability group (`start_finish` floaters) to
      `examples/farmers_market_full/schedule.yaml`.
- [ ] `uv run compute` → clean; confirm floaters have correct dates and draw no arrows.

## Phase 6 — Review
- [ ] Stop before committing. User reviews all changes.

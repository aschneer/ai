"""Render a static HTML Gantt chart from a computed schedule."""

from __future__ import annotations

import html
from datetime import date, timedelta

from schedule.compute_lib import ComputedSchedule, ScheduleItem
from schedule.kinds_lib import ItemKind


def render_gantt_html(result: ComputedSchedule, *, title: str = "Schedule") -> str:
    """Return a self-contained HTML document for the computed schedule."""
    by_id = {item.id: item for item in result.items}
    date_range = _date_range(result)
    if date_range is None:
        return _empty_html(title)

    range_start, range_end = date_range
    total_days = (range_end - range_start).days + 1
    week_columns = _week_columns(range_start, range_end)
    rows = "".join(_render_row(item, by_id, range_start, total_days) for item in result.items)
    finish_label = result.project_finish.isoformat() if result.project_finish else "—"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #fafafa;
      --grid: #e8e8e8;
      --text: #1a1a1a;
      --muted: #666;
      --task: #4a7fd4;
      --group: #7a9e7a;
      --milestone: #c45c26;
      --label-width: 16rem;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, sans-serif;
      font-size: 14px;
      color: var(--text);
      background: var(--bg);
    }}
    header {{
      padding: 1rem 1.25rem;
      border-bottom: 1px solid var(--grid);
      background: #fff;
    }}
    header h1 {{
      margin: 0 0 0.25rem;
      font-size: 1.25rem;
      font-weight: 600;
    }}
    header p {{
      margin: 0;
      color: var(--muted);
    }}
    .gantt {{
      overflow-x: auto;
      padding: 0 0 1rem;
    }}
    .gantt-inner {{
      min-width: 48rem;
    }}
    .row {{
      display: grid;
      grid-template-columns: var(--label-width) 1fr;
      border-bottom: 1px solid var(--grid);
      min-height: 2rem;
      background: #fff;
    }}
    .row.header {{
      position: sticky;
      top: 0;
      z-index: 2;
      background: #f3f3f3;
      font-size: 0.75rem;
      color: var(--muted);
      min-height: 1.75rem;
    }}
    .label {{
      padding: 0.35rem 0.75rem;
      border-right: 1px solid var(--grid);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .label .kind {{
      color: var(--muted);
      font-size: 0.7rem;
      margin-right: 0.35rem;
    }}
    .timeline {{
      position: relative;
      min-height: 2rem;
    }}
    .timeline-header {{
      display: flex;
      height: 100%;
    }}
    .week {{
      flex: 1;
      border-right: 1px solid var(--grid);
      padding: 0.25rem 0.35rem;
      text-align: center;
    }}
    .bar-area {{
      position: absolute;
      inset: 0.3rem 0;
    }}
    .bar {{
      position: absolute;
      top: 0.25rem;
      height: calc(100% - 0.5rem);
      border-radius: 3px;
      min-width: 2px;
    }}
    .bar.task {{ background: var(--task); }}
    .bar.group {{ background: var(--group); opacity: 0.85; }}
    .bar.milestone {{
      width: 10px !important;
      min-width: 10px;
      margin-left: -5px;
      background: var(--milestone);
      border-radius: 50%;
      top: 50%;
      height: 10px;
      transform: translateY(-50%);
    }}
    .dates {{
      font-size: 0.7rem;
      color: var(--muted);
      padding-left: 0.75rem;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <p>Project finish: {html.escape(finish_label)}</p>
  </header>
  <div class="gantt">
    <div class="gantt-inner">
      <div class="row header">
        <div class="label">Item</div>
        <div class="timeline">
          <div class="timeline-header">{week_columns}</div>
        </div>
      </div>
      {rows}
    </div>
  </div>
</body>
</html>
"""


def _empty_html(title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
</head>
<body><p>No scheduled items to display.</p></body>
</html>
"""


def _date_range(result: ComputedSchedule) -> tuple[date, date] | None:
    starts = [item.start for item in result.items if item.start is not None]
    finishes = [item.finish for item in result.items if item.finish is not None]
    if not starts or not finishes:
        return None
    return min(starts), max(finishes)


def _week_columns(range_start: date, range_end: date) -> str:
    columns: list[str] = []
    current = range_start - timedelta(days=range_start.weekday())
    while current <= range_end:
        label = current.strftime("%b %d")
        columns.append(f'<div class="week">{html.escape(label)}</div>')
        current += timedelta(days=7)
    return "".join(columns)


def _render_row(
    item: ScheduleItem,
    by_id: dict[int, ScheduleItem],
    range_start: date,
    total_days: int,
) -> str:
    depth = _item_depth(item, by_id)
    indent = "  " * depth
    kind_label = item.kind.value
    name = html.escape(f"{indent}{item.name}")
    date_text = _date_label(item)

    bar_html = ""
    if item.start is not None and item.finish is not None and total_days > 0:
        offset_days = (item.start - range_start).days
        span_days = max((item.finish - item.start).days + 1, 1)
        left_pct = offset_days / total_days * 100
        width_pct = span_days / total_days * 100
        if item.kind == ItemKind.MILESTONE:
            bar_html = (
                f'<div class="bar milestone" style="left: {left_pct:.2f}%;"></div>'
            )
        else:
            bar_html = (
                f'<div class="bar {item.kind.value}" '
                f'style="left: {left_pct:.2f}%; width: {width_pct:.2f}%;"></div>'
            )

    return f"""      <div class="row">
        <div class="label" title="{html.escape(item.name)}">
          <span class="kind">{kind_label}</span>{name}
          <div class="dates">{html.escape(date_text)}</div>
        </div>
        <div class="timeline">
          <div class="bar-area">{bar_html}</div>
        </div>
      </div>
"""


def _date_label(item: ScheduleItem) -> str:
    if item.start is None or item.finish is None:
        return "—"
    if item.kind == ItemKind.MILESTONE:
        return item.start.isoformat()
    if item.start == item.finish:
        return item.start.isoformat()
    return f"{item.start.isoformat()} → {item.finish.isoformat()}"


def _item_depth(item: ScheduleItem, by_id: dict[int, ScheduleItem]) -> int:
    level = 0
    parent_id = item.parent_id
    while parent_id is not None:
        level += 1
        parent = by_id.get(parent_id)
        if parent is None:
            break
        parent_id = parent.parent_id
    return level

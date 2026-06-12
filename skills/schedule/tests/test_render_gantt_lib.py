from datetime import date
from pathlib import Path

from schedule.compute_lib import compute_schedule
from schedule.io_lib import load_yaml
from schedule.render_gantt_lib import render_gantt_html

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "landscaping"
CALENDAR = {"weekends": ["sat", "sun"], "holidays": []}


def test_render_gantt_html_includes_items_and_finish() -> None:
    schedule_data = load_yaml(EXAMPLES / "schedule.yaml")
    calendar_data = load_yaml(EXAMPLES / "calendar.yaml")
    result = compute_schedule(schedule_data, calendar_data)
    html_content = render_gantt_html(result, title="Landscaping")

    assert "Landscaping" in html_content
    assert "Project finish: 2026-06-29" in html_content
    assert "Trim the hedges" in html_content
    assert "Permit approved" in html_content
    assert 'class="bar task"' in html_content
    assert 'class="bar milestone"' in html_content


def test_render_gantt_html_empty_schedule() -> None:
    from schedule.compute_lib import ComputedSchedule

    html_content = render_gantt_html(ComputedSchedule(items=[], project_finish=None))

    assert "No scheduled items" in html_content


def test_item_depth_indents_nested_rows() -> None:
    schedule_data = {
        "items": [
            {"kind": "milestone", "id": 0, "name": "Start", "date": "2026-06-09"},
            {
                "kind": "group",
                "id": 10,
                "name": "Group",
                "predecessors": ["0FS"],
                "children": [
                    {
                        "kind": "task",
                        "id": 11,
                        "name": "Child task",
                        "duration": "1d",
                        "predecessors": ["10SS"],
                    }
                ],
            },
        ]
    }
    result = compute_schedule(schedule_data, CALENDAR)
    html_content = render_gantt_html(result)

    assert "  Child task" in html_content

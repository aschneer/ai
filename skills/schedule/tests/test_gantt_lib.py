import json
from pathlib import Path

from schedule.compute_lib import computed_schedule_to_dict, compute_schedule
from schedule.gantt_lib import (
    GANTT_DATA_FILENAME,
    GANTT_HTML_FILENAME,
    GANTT_JS_FILENAME,
    deploy_gantt_assets,
    schedule_payload,
    write_gantt_data,
)
from schedule.io_lib import load_yaml

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "landscaping"
CALENDAR = {"weekends": ["sat", "sun"], "holidays": []}


def test_write_gantt_data_and_deploy_assets(tmp_path: Path) -> None:
    schedule_data = load_yaml(EXAMPLES / "schedule.yaml")
    calendar_data = load_yaml(EXAMPLES / "calendar.yaml")
    result = compute_schedule(schedule_data, calendar_data)
    payload = schedule_payload(computed_schedule_to_dict(result), title="Landscaping")

    data_path = tmp_path / GANTT_DATA_FILENAME
    write_gantt_data(data_path, payload)
    assets = deploy_gantt_assets(tmp_path)

    assert data_path.is_file()
    loaded = json.loads(data_path.read_text(encoding="utf-8"))
    assert loaded["title"] == "Landscaping"
    assert loaded["project_finish"] == "2026-06-29"
    assert any(item["name"] == "Trim the hedges" for item in loaded["items"])
    hedges = next(item for item in loaded["items"] if item["name"] == "Trim the hedges")
    pavers = next(item for item in loaded["items"] if item["name"] == "Install pavers")
    assert hedges["is_critical"] is False
    assert pavers["is_critical"] is True

    asset_names = {path.name for path in assets}
    assert asset_names == {GANTT_HTML_FILENAME, GANTT_JS_FILENAME}
    assert "fetch(" in (tmp_path / GANTT_JS_FILENAME).read_text(encoding="utf-8")
    assert GANTT_DATA_FILENAME in (tmp_path / GANTT_JS_FILENAME).read_text(encoding="utf-8")


def test_schedule_payload_adds_title() -> None:
    payload = schedule_payload({"project_finish": "2026-06-29", "items": []}, title="Demo")

    assert payload["title"] == "Demo"
    assert payload["project_finish"] == "2026-06-29"

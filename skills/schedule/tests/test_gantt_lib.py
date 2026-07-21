import json
from pathlib import Path

from schedule.compute_lib import computed_schedule_to_dict, compute_schedule
from schedule.gantt_lib import (
    GANTT_DATA_FILENAME,
    GANTT_HTML_FILENAME,
    GANTT_JS_FILENAME,
    GANTT_THEME_FILENAME,
    PROJECT_GITIGNORE_FILENAME,
    RECOMPUTE_FILENAME,
    SITE_DIR,
    deploy_gantt_assets,
    deploy_project_gitignore,
    deploy_recompute_script,
    schedule_payload,
    site_directory,
    write_gantt_data,
)
from schedule.io_lib import load_yaml

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "home_renovation"
CALENDAR = {"weekends": ["sat", "sun"], "holidays": []}


def test_write_gantt_data_and_deploy_assets(tmp_path: Path) -> None:
    schedule_data = load_yaml(FIXTURES / "schedule.yaml")
    calendar_data = load_yaml(FIXTURES / "calendar.yaml")
    result = compute_schedule(schedule_data, calendar_data)
    payload = schedule_payload(computed_schedule_to_dict(result), title="Home renovation")

    data_path = site_directory(tmp_path) / GANTT_DATA_FILENAME
    write_gantt_data(data_path, payload)
    assets = deploy_gantt_assets(site_directory(tmp_path), build_token="12345")

    assert data_path.is_file()
    loaded = json.loads(data_path.read_text(encoding="utf-8"))
    assert loaded["title"] == "Home renovation"
    assert loaded["project_finish"] == "2026-09-10"
    assert any(item["name"] == "Demo kitchen" for item in loaded["items"])
    cabinets = next(item for item in loaded["items"] if item["name"] == "Install cabinets")
    punch = next(item for item in loaded["items"] if item["name"] == "Punch list closeout")
    assert cabinets["is_critical"] is False
    assert punch["is_critical"] is True

    asset_names = {path.name for path in assets}
    assert asset_names == {GANTT_HTML_FILENAME, GANTT_JS_FILENAME, GANTT_THEME_FILENAME}
    assert (tmp_path / SITE_DIR / GANTT_JS_FILENAME).is_file()
    assert "fetch(" in (tmp_path / SITE_DIR / GANTT_JS_FILENAME).read_text(encoding="utf-8")
    assert GANTT_DATA_FILENAME in (tmp_path / SITE_DIR / GANTT_JS_FILENAME).read_text(encoding="utf-8")

    html = (tmp_path / SITE_DIR / GANTT_HTML_FILENAME).read_text(encoding="utf-8")
    assert "__BUILD_TOKEN__" not in html
    assert "gantt.js?v=12345" in html
    assert "gantt_theme.css?v=12345" in html


def test_deploy_project_gitignore_writes_and_preserves(tmp_path: Path) -> None:
    written = deploy_project_gitignore(tmp_path)
    gitignore = tmp_path / PROJECT_GITIGNORE_FILENAME
    assert written == gitignore
    assert "site/" in gitignore.read_text(encoding="utf-8")

    # Existing .gitignore is never overwritten.
    gitignore.write_text("custom\n", encoding="utf-8")
    assert deploy_project_gitignore(tmp_path) is None
    assert gitignore.read_text(encoding="utf-8") == "custom\n"


def test_deploy_recompute_script_bakes_filename_and_is_executable(tmp_path: Path) -> None:
    written = deploy_recompute_script(tmp_path, "my_plan.yaml")
    script = tmp_path / RECOMPUTE_FILENAME
    assert written == script

    text = script.read_text(encoding="utf-8")
    assert '"$proj/my_plan.yaml"' in text
    assert "{schedule_filename}" not in text
    assert '"$HOME/.aschneer/skills/personal_skills/schedule"' in text
    assert script.stat().st_mode & 0o111  # executable

    # Overwritten on rerun with a new schedule filename.
    deploy_recompute_script(tmp_path, "other.yaml")
    assert '"$proj/other.yaml"' in script.read_text(encoding="utf-8")


def test_schedule_payload_adds_title() -> None:
    payload = schedule_payload({"project_finish": "2026-06-29", "items": []}, title="Demo")

    assert payload["title"] == "Demo"
    assert payload["project_finish"] == "2026-06-29"

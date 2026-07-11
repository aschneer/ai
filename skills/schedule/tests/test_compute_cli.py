import json
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "home_renovation"
SKILL_ROOT = Path(__file__).resolve().parent.parent


def test_compute_cli_writes_gantt_files(tmp_path: Path) -> None:
    schedule_copy = tmp_path / "schedule.yaml"
    calendar_copy = tmp_path / "calendar.yaml"
    schedule_copy.write_text((FIXTURES / "schedule.yaml").read_text(encoding="utf-8"))
    calendar_copy.write_text((FIXTURES / "calendar.yaml").read_text(encoding="utf-8"))

    result = subprocess.run(
        [
            "uv",
            "run",
            "compute",
            str(schedule_copy),
            "--no-serve",
            "--no-stdout",
        ],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    site = tmp_path / "site"
    assert (site / "gantt_data.json").is_file()
    assert (site / "gantt.html").is_file()
    assert (site / "gantt.js").is_file()
    assert (site / "gantt_theme.css").is_file()
    payload = json.loads((site / "gantt_data.json").read_text(encoding="utf-8"))
    assert payload["project_finish"] == "2026-09-10"
    # Title comes from the schedule's required title: field.
    assert payload["title"] == "Home Renovation"


def _copy_fixture(tmp_path: Path) -> Path:
    (tmp_path / "calendar.yaml").write_text(
        (FIXTURES / "calendar.yaml").read_text(encoding="utf-8")
    )
    schedule_copy = tmp_path / "schedule.yaml"
    schedule_copy.write_text((FIXTURES / "schedule.yaml").read_text(encoding="utf-8"))
    return schedule_copy


def test_compute_cli_title_flag_overrides_field(tmp_path: Path) -> None:
    schedule_copy = _copy_fixture(tmp_path)

    result = subprocess.run(
        ["uv", "run", "compute", str(schedule_copy), "--title", "Override", "--no-serve", "--no-stdout"],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((tmp_path / "site" / "gantt_data.json").read_text(encoding="utf-8"))
    assert payload["title"] == "Override"


def test_compute_cli_missing_title_fails_validation(tmp_path: Path) -> None:
    schedule_copy = _copy_fixture(tmp_path)
    lines = schedule_copy.read_text(encoding="utf-8").splitlines(keepends=True)
    schedule_copy.write_text("".join(l for l in lines if not l.startswith("title:")))

    result = subprocess.run(
        ["uv", "run", "compute", str(schedule_copy), "--no-serve", "--no-stdout"],
        cwd=SKILL_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "title" in result.stderr
    assert not (tmp_path / "site").exists()

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
    assert (tmp_path / "gantt_data.json").is_file()
    assert (tmp_path / "gantt.html").is_file()
    assert (tmp_path / "gantt.js").is_file()
    payload = json.loads((tmp_path / "gantt_data.json").read_text(encoding="utf-8"))
    assert payload["project_finish"] == "2026-09-10"

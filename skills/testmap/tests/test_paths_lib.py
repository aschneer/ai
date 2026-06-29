"""Tests for output-directory and schema path resolution."""

from __future__ import annotations

from pathlib import Path

from testmap import paths_lib


def test_schema_path_builds_yaml_name() -> None:
    assert paths_lib.schema_path("index").name == "index.schema.yaml"
    assert paths_lib.schema_path("index").parent == paths_lib.SCHEMAS_DIR


def test_output_dir_is_under_target() -> None:
    target = Path("/tmp/proj")
    assert paths_lib.output_dir(target) == target / "testmap_output"


def test_output_dir_resolves_relative_target() -> None:
    # A relative target is resolved to an absolute output dir.
    assert paths_lib.output_dir(Path(".")).is_absolute()


def test_data_file_lives_at_output_root() -> None:
    target = Path("/tmp/proj")
    assert paths_lib.data_file(target, "index.json") == target / "testmap_output" / "index.json"


def test_temp_and_report_dirs() -> None:
    target = Path("/tmp/proj")
    assert paths_lib.temp_dir(target) == target / "testmap_output" / "temp"
    assert paths_lib.report_dir(target) == target / "testmap_output" / "report"


def test_ensure_output_dir_creates_dir_and_gitignore(tmp_path: Path) -> None:
    out = paths_lib.ensure_output_dir(tmp_path)
    assert out.is_dir()
    gitignore = out / ".gitignore"
    assert gitignore.is_file()
    assert "temp/" in gitignore.read_text()


def test_ensure_output_dir_is_idempotent(tmp_path: Path) -> None:
    # Running twice must not error or duplicate, and must preserve a custom gitignore.
    paths_lib.ensure_output_dir(tmp_path)
    (paths_lib.output_dir(tmp_path) / ".gitignore").write_text("temp/\ncustom/\n")
    paths_lib.ensure_output_dir(tmp_path)
    assert "custom/" in (paths_lib.output_dir(tmp_path) / ".gitignore").read_text()

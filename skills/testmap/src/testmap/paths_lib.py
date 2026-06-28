"""Filesystem paths: skill-local schemas and target output-directory layout."""

from __future__ import annotations

from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = SKILL_ROOT / "schemas"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

OUTPUT_DIR_NAME = "testmap_output"


def schema_path(name: str) -> Path:
    """Return the path to ``schemas/<name>.schema.yaml``."""
    return SCHEMAS_DIR / f"{name}.schema.yaml"


def output_dir(target_dir: Path) -> Path:
    """Return the ``testmap_output/`` directory for a target directory (PRD 1.2)."""
    return target_dir.resolve() / OUTPUT_DIR_NAME


def ensure_output_dir(target_dir: Path) -> Path:
    """Create the output directory and write its ``.gitignore`` for ``temp/`` (PRD 1.3.3).

    The output folder ships its own gitignore so the ephemeral temp/ is excluded in
    the target repo without the user configuring anything.
    """
    out = output_dir(target_dir)
    out.mkdir(parents=True, exist_ok=True)
    gitignore = out / ".gitignore"
    if not gitignore.is_file():
        gitignore.write_text("temp/\n", encoding="utf-8")
    return out


def data_file(target_dir: Path, name: str) -> Path:
    """Return the path to a committed data file at the output-dir root (PRD 1.3.1)."""
    return output_dir(target_dir) / name


def temp_dir(target_dir: Path) -> Path:
    """Return the gitignored ``temp/`` subfolder for ephemeral files (PRD 1.3.3)."""
    return output_dir(target_dir) / "temp"


def report_dir(target_dir: Path) -> Path:
    """Return the ``report/`` subfolder for static rendering assets (PRD 1.3.2)."""
    return output_dir(target_dir) / "report"

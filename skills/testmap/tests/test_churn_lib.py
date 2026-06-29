"""Tests for the git churn signal."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from testmap import churn_lib


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t.co")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.py").write_text("x = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "first")
    (tmp_path / "a.py").write_text("x = 2\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "second")
    return tmp_path


def test_is_git_repo_true_for_repo(git_repo: Path) -> None:
    assert churn_lib.is_git_repo(git_repo) is True


def test_is_git_repo_false_for_plain_dir(tmp_path: Path) -> None:
    assert churn_lib.is_git_repo(tmp_path) is False


def test_repo_toplevel_returns_root(git_repo: Path) -> None:
    assert churn_lib.repo_toplevel(git_repo) == git_repo.resolve()


def test_repo_toplevel_none_outside_repo(tmp_path: Path) -> None:
    assert churn_lib.repo_toplevel(tmp_path) is None


def test_file_churn_counts_commits_touching_file(git_repo: Path) -> None:
    churn = churn_lib.file_churn(git_repo, {"a.py"})
    assert churn["a.py"] == 2


def test_file_churn_zero_for_untouched_path(git_repo: Path) -> None:
    churn = churn_lib.file_churn(git_repo, {"missing.py"})
    assert churn["missing.py"] == 0


def test_file_churn_all_zero_outside_repo(tmp_path: Path) -> None:
    assert churn_lib.file_churn(tmp_path, {"a.py"}) == {"a.py": 0}

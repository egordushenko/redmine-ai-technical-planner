import subprocess
from pathlib import Path

import pytest

from app.git.repo_manager import GitCommandError, MissingProjectMappingError, RepoManager


def test_resolve_project_mapping(tmp_path: Path):
    projects_file = tmp_path / "projects.yaml"
    projects_file.write_text(
        """
projects:
  demo:
    repo_url: "git@example.com:demo.git"
    branch: "main"
    local_dir: "demo-repo"
""".strip(),
        encoding="utf-8",
    )

    manager = RepoManager(projects_file, tmp_path / "repos")

    config = manager.get_project_config("demo")

    assert config.repo_url == "git@example.com:demo.git"
    assert config.branch == "main"
    assert config.local_dir == "demo-repo"


def test_missing_project_mapping(tmp_path: Path):
    projects_file = tmp_path / "projects.yaml"
    projects_file.write_text("projects: {}\n", encoding="utf-8")

    manager = RepoManager(projects_file, tmp_path / "repos")

    with pytest.raises(MissingProjectMappingError):
        manager.get_project_config("unknown")


def test_git_command_error_sanitizes_secret_url(tmp_path: Path, monkeypatch):
    manager = RepoManager(tmp_path / "projects.yaml", tmp_path / "repos")

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            128,
            ["git", "clone", "https://user:secret-token@example.com/repo.git"],
            stderr="fatal: https://user:secret-token@example.com/repo.git failed token=secret-token",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(GitCommandError) as exc:
        manager._run_git(["clone", "https://user:secret-token@example.com/repo.git"], tmp_path)

    message = str(exc.value)
    assert "secret-token" not in message
    assert "<redacted>" in message

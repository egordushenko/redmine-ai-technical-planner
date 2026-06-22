from pathlib import Path

import pytest

from app.git.repo_manager import MissingProjectMappingError, RepoManager


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

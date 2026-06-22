from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class MissingProjectMappingError(KeyError):
    pass


@dataclass(frozen=True)
class ProjectRepoConfig:
    repo_url: str
    branch: str = "main"
    local_dir: str | None = None


class RepoManager:
    def __init__(self, projects_yaml_path: Path | str, repos_base_dir: Path | str):
        self.projects_yaml_path = Path(projects_yaml_path)
        self.repos_base_dir = Path(repos_base_dir)

    def _load_mapping(self) -> dict[str, Any]:
        if not self.projects_yaml_path.exists():
            raise FileNotFoundError(f"projects.yaml not found: {self.projects_yaml_path}")
        data = yaml.safe_load(self.projects_yaml_path.read_text(encoding="utf-8")) or {}
        return data.get("projects") or {}

    def get_project_config(self, project_identifier: str) -> ProjectRepoConfig:
        projects = self._load_mapping()
        raw_config = projects.get(project_identifier)
        if not raw_config:
            raise MissingProjectMappingError(project_identifier)
        return ProjectRepoConfig(
            repo_url=str(raw_config["repo_url"]),
            branch=str(raw_config.get("branch") or "main"),
            local_dir=raw_config.get("local_dir") or project_identifier,
        )

    def ensure_repo(self, project_identifier: str) -> Path:
        config = self.get_project_config(project_identifier)
        local_path = self.repos_base_dir / (config.local_dir or project_identifier)
        self.repos_base_dir.mkdir(parents=True, exist_ok=True)
        if not local_path.exists():
            self._run_git(["clone", "--branch", config.branch, config.repo_url, str(local_path)], cwd=self.repos_base_dir)
            return local_path
        self._run_git(["fetch", "--all", "--prune"], cwd=local_path)
        self._run_git(["checkout", config.branch], cwd=local_path)
        self._run_git(["pull", "--ff-only"], cwd=local_path)
        return local_path

    def _run_git(self, args: list[str], cwd: Path) -> None:
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)

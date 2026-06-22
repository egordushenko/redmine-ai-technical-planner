from pathlib import Path

from app.config import Settings
from app.git.repo_manager import RepoManager
from app.llm.client import LLMResponse
from app.llm.schemas import AnalysisResult, FileChangePlan
from app.planner.analyzer import Analyzer
from app.redmine.models import Issue, Project
from app.storage.state import StateStore


class FakeRedmineClient:
    def __init__(self):
        self.comments: list[tuple[int, str]] = []
        self.issue = Issue(
            id=123,
            subject="Fix login redirect",
            description="The login callback loses redirect URL.",
            project=Project(id=1, name="Demo", identifier="demo"),
            updated_on="2026-06-22T10:00:00Z",
        )

    def get_issue(self, issue_id: int) -> Issue:
        assert issue_id == 123
        return self.issue

    def get_project(self, project_id: int) -> Project:
        return Project(id=project_id, name="Demo", identifier="demo")

    def add_issue_comment(self, issue_id: int, markdown: str) -> None:
        self.comments.append((issue_id, markdown))


class FakeLLMClient:
    model = "fake"

    def analyze(self, issue_context: str, repo_context: str) -> LLMResponse:
        assert "Fix login redirect" in issue_context
        assert "src/auth.py" in repo_context
        return LLMResponse(
            result=AnalysisResult(
                task_understanding="Нужно исправить redirect после логина.",
                files_to_change=[
                    FileChangePlan(
                        path="src/auth.py",
                        relevance_reason="Содержит login callback.",
                        suggested_changes=["Сохранить redirect URL."],
                        confidence="high",
                    )
                ],
                implementation_plan=["Обновить auth flow."],
                verification_steps=["Проверить возврат на исходный URL."],
                risks=[],
                analysis_limits=["Dry-run."],
            ),
            latency_seconds=0.01,
        )


class FakeRepoManager:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def ensure_repo(self, project_identifier: str) -> Path:
        assert project_identifier == "demo"
        return self.repo_path


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        redmine_base_url="https://redmine.test",
        redmine_api_key="secret",
        llm_base_url="https://llm.test/v1",
        llm_api_key="secret",
        llm_model="fake-model",
        repos_base_dir=tmp_path / "repos",
        bot_signature="bot",
        max_files_to_analyze=12,
        max_chars_per_file=12000,
        max_total_context_chars=80000,
        state_db_path=tmp_path / "state.sqlite3",
        log_level="INFO",
        projects_yaml_path=tmp_path / "projects.yaml",
        post_errors_to_redmine=False,
    )


def test_analyze_issue_dry_run_does_not_post_comment(tmp_path: Path):
    repo = tmp_path / "repos" / "demo-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "auth.py").write_text("def login_callback(): pass\n", encoding="utf-8")
    projects = tmp_path / "projects.yaml"
    projects.write_text(
        """
projects:
  demo:
    repo_url: "git@example.com:demo.git"
    branch: "main"
    local_dir: "demo-repo"
""".strip(),
        encoding="utf-8",
    )
    settings = _settings(tmp_path)
    redmine = FakeRedmineClient()
    analyzer = Analyzer(settings, redmine, FakeRepoManager(repo), FakeLLMClient(), StateStore(settings.state_db_path))

    output = analyzer.analyze_issue(123, dry_run=True)

    assert not output.posted
    assert not redmine.comments
    assert "src/auth.py" in output.markdown


def test_analyze_issue_skips_unchanged_processed_issue(tmp_path: Path):
    settings = _settings(tmp_path)
    redmine = FakeRedmineClient()
    state = StateStore(settings.state_db_path)
    state.mark_processed(123, redmine.issue.updated_on, "demo", "hash")
    analyzer = Analyzer(settings, redmine, RepoManager(settings.projects_yaml_path, settings.repos_base_dir), FakeLLMClient(), state)

    output = analyzer.analyze_issue(123, dry_run=False)

    assert output.skipped
    assert not redmine.comments

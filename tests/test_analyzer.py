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
        self.created_issues: list[dict] = []
        self.child_issues: list[Issue] = []
        self._return_refreshed_issue = False
        self.issue = Issue(
            id=123,
            subject="Fix login redirect",
            description="The login callback loses redirect URL.",
            project=Project(id=1, name="Demo", identifier="demo"),
            updated_on="2026-06-22T10:00:00Z",
            tracker={"id": 1, "name": "Bug"},
            priority={"id": 2, "name": "Normal"},
        )
        self.refreshed_issue = Issue(
            id=123,
            subject=self.issue.subject,
            description=self.issue.description,
            project=self.issue.project,
            updated_on="2026-06-22T10:01:00Z",
            tracker=self.issue.tracker,
            priority=self.issue.priority,
        )

    def get_issue(self, issue_id: int) -> Issue:
        assert issue_id == 123
        if self._return_refreshed_issue:
            return self.refreshed_issue
        return self.issue

    def get_project(self, project_id: int) -> Project:
        return Project(id=project_id, name="Demo", identifier="demo")

    def add_issue_comment(self, issue_id: int, markdown: str) -> None:
        self.comments.append((issue_id, markdown))

    def update_issue(self, issue_id: int, **fields) -> None:
        self.comments.append((issue_id, fields.get("notes", "")))
        self.updated_fields = fields
        self._return_refreshed_issue = True

    def get_issue_status_id_by_name(self, name: str) -> int:
        assert name == "In Progress"
        return 2

    def get_issue_priority_id_by_name(self, name: str) -> int:
        assert name == "High"
        return 3

    def create_issue(self, **fields) -> int:
        self.created_issues.append(fields)
        return 1000 + len(self.created_issues)

    def list_child_issues(self, parent_issue_id: int) -> list[Issue]:
        assert parent_issue_id == 123
        return self.child_issues


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
                subtasks=["Обновить auth middleware.", "Добавить тест redirect."],
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


class FakeUnstructuredLLMClient:
    def analyze(self, issue_context: str, repo_context: str) -> LLMResponse:
        return LLMResponse(
            result=AnalysisResult(
                task_understanding="Structured parsing failed.",
                files_to_change=[],
                implementation_plan=[],
                verification_steps=[],
                risks=["raw fallback"],
                analysis_limits=["invalid json"],
                raw_text="not json",
                structured=False,
            ),
            latency_seconds=0.01,
        )


class FakeHallucinatedPathLLMClient:
    def analyze(self, issue_context: str, repo_context: str) -> LLMResponse:
        return LLMResponse(
            result=AnalysisResult(
                task_understanding="Fix login redirect.",
                files_to_change=[
                    FileChangePlan(
                        path="src/auth.py",
                        relevance_reason="Selected context file.",
                        suggested_changes=["Patch callback."],
                        confidence="high",
                    ),
                    FileChangePlan(
                        path="src/not_in_context.py",
                        relevance_reason="Hallucinated file.",
                        suggested_changes=["Patch it."],
                        confidence="medium",
                    ),
                ],
                implementation_plan=["Patch callback."],
                verification_steps=["Run tests."],
                risks=[],
                analysis_limits=[],
            ),
            latency_seconds=0.01,
        )


class FakeSparseLLMClient:
    def analyze(self, issue_context: str, repo_context: str) -> LLMResponse:
        return LLMResponse(
            result=AnalysisResult(
                task_understanding="Fix login redirect.",
                files_to_change=[
                    FileChangePlan(
                        path="src/auth.py",
                        relevance_reason="Selected context file.",
                        suggested_changes=["Patch callback."],
                        confidence="high",
                    )
                ],
                implementation_plan=[
                    "Update auth middleware.",
                    "Add redirect regression test.",
                    "Run CLI smoke check.",
                ],
                subtasks=[],
                effort_estimate="",
                verification_steps=[],
                risks=[],
                analysis_limits=[],
            ),
            latency_seconds=0.01,
        )


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
        redmine_update_issue_after_plan=False,
        redmine_after_plan_status_name="In Progress",
        redmine_after_plan_priority_name="High",
        redmine_after_plan_done_ratio=50,
        redmine_create_subtasks_after_plan=False,
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


def test_analyze_issue_updates_redmine_fields_after_plan(tmp_path: Path):
    repo = tmp_path / "repos" / "demo-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "auth.py").write_text("def login_callback(): pass\n", encoding="utf-8")
    settings = _settings(tmp_path)
    settings = Settings(**{**settings.__dict__, "redmine_update_issue_after_plan": True})
    redmine = FakeRedmineClient()
    analyzer = Analyzer(settings, redmine, FakeRepoManager(repo), FakeLLMClient(), StateStore(settings.state_db_path))

    output = analyzer.analyze_issue(123, dry_run=False)

    assert output.posted
    assert redmine.updated_fields["status_id"] == 2
    assert redmine.updated_fields["done_ratio"] == 50
    assert redmine.updated_fields["priority_id"] == 3
    assert StateStore(settings.state_db_path).is_already_processed(123, redmine.refreshed_issue.updated_on)


def test_analyze_issue_creates_redmine_subtasks_after_plan(tmp_path: Path):
    repo = tmp_path / "repos" / "demo-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "auth.py").write_text("def login_callback(): pass\n", encoding="utf-8")
    settings = _settings(tmp_path)
    settings = Settings(
        **{
            **settings.__dict__,
            "redmine_update_issue_after_plan": True,
            "redmine_create_subtasks_after_plan": True,
        }
    )
    redmine = FakeRedmineClient()
    analyzer = Analyzer(settings, redmine, FakeRepoManager(repo), FakeLLMClient(), StateStore(settings.state_db_path))

    analyzer.analyze_issue(123, dry_run=False)

    assert len(redmine.created_issues) == 2
    assert redmine.created_issues[0]["parent_issue_id"] == 123
    assert redmine.created_issues[0]["project_id"] == 1
    assert redmine.created_issues[0]["tracker_id"] == 1
    assert redmine.created_issues[0]["priority_id"] == 3
    assert redmine.created_issues[0]["subject"] == "Обновить auth middleware."


def test_analyze_issue_does_not_update_fields_or_create_subtasks_for_unstructured_fallback(tmp_path: Path):
    repo = tmp_path / "repos" / "demo-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "auth.py").write_text("def login_callback(): pass\n", encoding="utf-8")
    settings = _settings(tmp_path)
    settings = Settings(
        **{
            **settings.__dict__,
            "redmine_update_issue_after_plan": True,
            "redmine_create_subtasks_after_plan": True,
        }
    )
    redmine = FakeRedmineClient()
    analyzer = Analyzer(settings, redmine, FakeRepoManager(repo), FakeUnstructuredLLMClient(), StateStore(settings.state_db_path))

    output = analyzer.analyze_issue(123, dry_run=False)

    assert output.posted
    assert not hasattr(redmine, "updated_fields")
    assert not redmine.created_issues
    assert redmine.comments


def test_analyze_issue_excludes_hallucinated_file_paths_from_comment(tmp_path: Path):
    repo = tmp_path / "repos" / "demo-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "auth.py").write_text("def login_callback(): pass\n", encoding="utf-8")
    settings = _settings(tmp_path)
    redmine = FakeRedmineClient()
    analyzer = Analyzer(settings, redmine, FakeRepoManager(repo), FakeHallucinatedPathLLMClient(), StateStore(settings.state_db_path))

    output = analyzer.analyze_issue(123, dry_run=True)

    assert "src/auth.py" in output.markdown
    assert "src/not_in_context.py" not in output.markdown
    assert "outside the provided repository context" in output.markdown
    risk_section = output.markdown.split("### 7. Риски и неопределённости", 1)[1].split("### 8.", 1)[0]
    assert "outside the provided repository context" not in risk_section


def test_analyze_issue_skips_duplicate_subtasks(tmp_path: Path):
    repo = tmp_path / "repos" / "demo-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "auth.py").write_text("def login_callback(): pass\n", encoding="utf-8")
    settings = _settings(tmp_path)
    settings = Settings(
        **{
            **settings.__dict__,
            "redmine_update_issue_after_plan": True,
            "redmine_create_subtasks_after_plan": True,
        }
    )
    redmine = FakeRedmineClient()
    redmine.child_issues = [
        Issue(
            id=200,
            subject="Обновить auth middleware.",
            description="Existing child",
            project=redmine.issue.project,
            updated_on="2026-06-22T10:00:00Z",
        )
    ]
    analyzer = Analyzer(settings, redmine, FakeRepoManager(repo), FakeLLMClient(), StateStore(settings.state_db_path))

    analyzer.analyze_issue(123, dry_run=False)

    assert len(redmine.created_issues) == 1


def test_analyze_issue_derives_demo_fields_when_model_omits_them(tmp_path: Path):
    repo = tmp_path / "repos" / "demo-repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "auth.py").write_text("def login_callback(): pass\n", encoding="utf-8")
    settings = _settings(tmp_path)
    settings = Settings(
        **{
            **settings.__dict__,
            "redmine_update_issue_after_plan": True,
            "redmine_create_subtasks_after_plan": True,
        }
    )
    redmine = FakeRedmineClient()
    analyzer = Analyzer(settings, redmine, FakeRepoManager(repo), FakeSparseLLMClient(), StateStore(settings.state_db_path))

    output = analyzer.analyze_issue(123, dry_run=False)

    assert output.posted
    assert "### 4. Подзадачи" in output.markdown
    assert "Update auth middleware." in output.markdown
    assert "### 5. Оценка временных затрат" in output.markdown
    assert "2-4 часа" in output.markdown
    assert "### 6. Что проверить после изменений" in output.markdown
    assert "Run project tests" in output.markdown
    assert len(redmine.created_issues) == 3
    assert redmine.created_issues[0]["subject"] == "Update auth middleware."

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from app.code_index.context_builder import build_issue_context, build_repo_context
from app.code_index.scanner import build_repo_tree, collect_important_files, list_source_files
from app.code_index.search import extract_keywords, score_files
from app.config import Settings
from app.git.repo_manager import MissingProjectMappingError, RepoManager
from app.llm.client import LLMClient
from app.llm.schemas import AnalysisResult
from app.planner.formatter import format_error_comment, format_success_comment
from app.redmine.client import RedmineClient, RedmineError
from app.storage.state import StateStore
from app.utils.text import sha256_text


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalyzeOutput:
    markdown: str
    posted: bool
    skipped: bool = False


class Analyzer:
    def __init__(
        self,
        settings: Settings,
        redmine_client: RedmineClient,
        repo_manager: RepoManager,
        llm_client: LLMClient,
        state_store: StateStore,
    ):
        self.settings = settings
        self.redmine_client = redmine_client
        self.repo_manager = repo_manager
        self.llm_client = llm_client
        self.state_store = state_store

    def analyze_issue(self, issue_id: int, dry_run: bool = False) -> AnalyzeOutput:
        issue = self.redmine_client.get_issue(issue_id)
        project_identifier = issue.project.identifier
        if not project_identifier and issue.project.id is not None:
            project_identifier = self.redmine_client.get_project(issue.project.id).identifier
        if not project_identifier:
            raise ValueError(f"Project identifier is missing for issue {issue_id}")
        if not dry_run and self.state_store.is_already_processed(issue.id, issue.updated_on):
            logger.info("issue already processed", extra={"issue_id": issue.id, "project_identifier": project_identifier})
            return AnalyzeOutput(markdown="", posted=False, skipped=True)
        try:
            repo_path = self.repo_manager.ensure_repo(project_identifier)
        except MissingProjectMappingError as exc:
            markdown = format_error_comment(
                f"для проекта `{project_identifier}` не найден Git-репозиторий в `projects.yaml`.",
                f"Добавьте mapping для `{project_identifier}` в projects.yaml.",
            )
            if self.settings.post_errors_to_redmine and not dry_run:
                self.redmine_client.add_issue_comment(issue.id, markdown)
            if not dry_run:
                self.state_store.mark_failed(issue.id, issue.updated_on, project_identifier, str(exc))
            return AnalyzeOutput(markdown=markdown, posted=self.settings.post_errors_to_redmine and not dry_run)
        try:
            files = list_source_files(repo_path)
            keywords = extract_keywords(issue)
            selected = score_files(issue, files, repo_path)[: self.settings.max_files_to_analyze]
            logger.info(
                "repository scanned",
                extra={
                    "issue_id": issue.id,
                    "project_identifier": project_identifier,
                    "repo_path": str(repo_path),
                    "number_of_files_scanned": len(files),
                    "candidate_files_count": len(selected),
                    "selected_files": [item.relative_path for item in selected],
                    "llm_model": self.settings.llm_model,
                },
            )
            repo_context = build_repo_context(
                Path(repo_path),
                build_repo_tree(repo_path),
                selected,
                keywords,
                self.settings.max_chars_per_file,
                self.settings.max_total_context_chars,
            )
            llm_response = self.llm_client.analyze(build_issue_context(issue), repo_context)
            allowed_paths = {item.relative_path for item in selected}
            allowed_paths.update(collect_important_files(repo_path).keys())
            result = _filter_files_to_context(llm_response.result, allowed_paths)
            result = _fill_demo_fallbacks(result)
            logger.info("llm analysis completed", extra={"issue_id": issue.id, "llm_latency": llm_response.latency_seconds})
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            markdown = format_success_comment(result, self.settings.llm_model, timestamp)
            posted = False
            if not dry_run:
                status_id = None
                priority_id = None
                if result.structured and self.settings.redmine_update_issue_after_plan:
                    status_id = self._resolve_status_id()
                    priority_id = self._resolve_priority_id()
                    self.redmine_client.update_issue(
                        issue.id,
                        notes=markdown,
                        status_id=status_id,
                        done_ratio=self.settings.redmine_after_plan_done_ratio,
                        priority_id=priority_id,
                    )
                else:
                    self.redmine_client.add_issue_comment(issue.id, markdown)
                if result.structured and self.settings.redmine_create_subtasks_after_plan:
                    self._create_subtasks(issue, result.subtasks, priority_id)
                posted = True
                refreshed_issue = self.redmine_client.get_issue(issue.id)
                self.state_store.mark_processed(issue.id, refreshed_issue.updated_on, project_identifier, sha256_text(markdown))
            logger.info("analysis finished", extra={"issue_id": issue.id, "comment_posted": posted})
            return AnalyzeOutput(markdown=markdown, posted=posted)
        except Exception as exc:
            markdown = format_error_comment(str(exc))
            logger.exception("analysis failed", extra={"issue_id": issue.id, "project_identifier": project_identifier})
            if not dry_run:
                self.state_store.mark_failed(issue.id, issue.updated_on, project_identifier, str(exc))
                if self.settings.post_errors_to_redmine:
                    self.redmine_client.add_issue_comment(issue.id, markdown)
                    return AnalyzeOutput(markdown=markdown, posted=True)
            return AnalyzeOutput(markdown=markdown, posted=False)

    def _resolve_status_id(self) -> int | None:
        try:
            return self.redmine_client.get_issue_status_id_by_name(self.settings.redmine_after_plan_status_name)
        except RedmineError:
            logger.warning("redmine status was not resolved; status update skipped", exc_info=True)
            return None

    def _resolve_priority_id(self) -> int | None:
        try:
            return self.redmine_client.get_issue_priority_id_by_name(self.settings.redmine_after_plan_priority_name)
        except RedmineError:
            logger.warning("redmine priority was not resolved; priority update skipped", exc_info=True)
            return None

    def _create_subtasks(self, issue, subtasks: list[str], priority_id: int | None) -> None:
        if not issue.project.id:
            logger.warning("project id is missing; subtask creation skipped", extra={"issue_id": issue.id})
            return
        tracker_id = int(issue.tracker["id"]) if issue.tracker and issue.tracker.get("id") else None
        if priority_id is None and issue.priority and issue.priority.get("id"):
            priority_id = int(issue.priority["id"])
        existing_subjects = set()
        try:
            existing_subjects = {_normalize_subject(child.subject) for child in self.redmine_client.list_child_issues(issue.id)}
        except Exception:
            logger.warning("could not load existing child issues; duplicate subtask check skipped", exc_info=True)
        for subtask in subtasks:
            subject = subtask.strip()[:255]
            if not subject or _normalize_subject(subject) in existing_subjects:
                continue
            description = "\n".join(
                [
                    "Generated from AI technical plan.",
                    "",
                    f"Parent issue: #{issue.id}",
                    f"Task: {subtask.strip()}",
                ]
            )
            try:
                self.redmine_client.create_issue(
                    project_id=int(issue.project.id),
                    subject=subject,
                    description=description,
                    parent_issue_id=issue.id,
                    tracker_id=tracker_id,
                    priority_id=priority_id,
                )
                existing_subjects.add(_normalize_subject(subject))
            except Exception:
                logger.warning("redmine subtask creation failed", extra={"issue_id": issue.id, "subject": subject}, exc_info=True)


def _normalize_subject(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _filter_files_to_context(result: AnalysisResult, allowed_paths: set[str]) -> AnalysisResult:
    if not result.files_to_change:
        return result
    filtered = [item for item in result.files_to_change if item.path in allowed_paths]
    if len(filtered) == len(result.files_to_change):
        return result
    note = "The model suggested file paths outside the provided repository context; those paths were excluded from the final plan."
    analysis_limits = list(result.analysis_limits)
    if note not in analysis_limits:
        analysis_limits.append(note)
    return replace(result, files_to_change=filtered, analysis_limits=analysis_limits)


def _fill_demo_fallbacks(result: AnalysisResult) -> AnalysisResult:
    if not result.structured:
        return result
    subtasks = result.subtasks or _derive_subtasks(result.implementation_plan)
    verification_steps = result.verification_steps or _derive_verification_steps(result.implementation_plan)
    effort_estimate = result.effort_estimate or _derive_effort_estimate(result)
    return replace(result, subtasks=subtasks, verification_steps=verification_steps, effort_estimate=effort_estimate)


def _derive_subtasks(implementation_plan: list[str]) -> list[str]:
    return [step.strip() for step in implementation_plan if step.strip()]


def _derive_verification_steps(implementation_plan: list[str]) -> list[str]:
    if not implementation_plan:
        return [
            "Run project tests.",
            "Run a smoke check for the changed user flow.",
            "Check the original Redmine acceptance scenario.",
        ]
    return [
        "Run project tests.",
        "Run a smoke check for the changed user flow.",
        "Verify the original issue scenario after implementation.",
    ]


def _derive_effort_estimate(result: AnalysisResult) -> str:
    complexity_score = len(result.files_to_change) + max(1, len(result.implementation_plan) // 3)
    if complexity_score <= 2:
        return "2-4 часа на реализацию и базовую проверку."
    if complexity_score <= 5:
        return "4-8 часов на реализацию, тесты и проверку сценария."
    return "1-2 рабочих дня на реализацию, тесты и регрессионную проверку."

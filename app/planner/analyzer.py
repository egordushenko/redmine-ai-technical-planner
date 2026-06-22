from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.code_index.context_builder import build_issue_context, build_repo_context
from app.code_index.scanner import build_repo_tree, list_source_files
from app.code_index.search import extract_keywords, score_files
from app.config import Settings
from app.git.repo_manager import MissingProjectMappingError, RepoManager
from app.llm.client import LLMClient
from app.planner.formatter import format_error_comment, format_success_comment
from app.redmine.client import RedmineClient
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
            logger.info("llm analysis completed", extra={"issue_id": issue.id, "llm_latency": llm_response.latency_seconds})
            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            markdown = format_success_comment(llm_response.result, self.settings.llm_model, timestamp)
            posted = False
            if not dry_run:
                if self.settings.redmine_update_issue_after_plan:
                    self.redmine_client.update_issue(
                        issue.id,
                        notes=markdown,
                        status_id=self.redmine_client.get_issue_status_id_by_name(self.settings.redmine_after_plan_status_name),
                        done_ratio=self.settings.redmine_after_plan_done_ratio,
                        priority_id=self.redmine_client.get_issue_priority_id_by_name(self.settings.redmine_after_plan_priority_name),
                    )
                else:
                    self.redmine_client.add_issue_comment(issue.id, markdown)
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

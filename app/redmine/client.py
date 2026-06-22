from __future__ import annotations

from typing import Any

import httpx

from app.redmine.models import Issue, Project


class RedmineError(RuntimeError):
    pass


class RedmineClient:
    def __init__(self, base_url: str, api_key: str, http_client: httpx.Client | None = None, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = http_client or httpx.Client(timeout=timeout)

    def _headers(self) -> dict[str, str]:
        return {
            "X-Redmine-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self._client.request(method, f"{self.base_url}{path}", headers=self._headers(), **kwargs)
        if response.status_code >= 400:
            raise RedmineError(f"Redmine API error {response.status_code}: {response.text}")
        if not response.content:
            return {}
        return response.json()

    def get_issue(self, issue_id: int) -> Issue:
        data = self._request("GET", f"/issues/{issue_id}.json", params={"include": "journals,attachments,relations"})
        return Issue.from_api(data["issue"])

    def get_project(self, project_id_or_identifier: int | str) -> Project:
        data = self._request("GET", f"/projects/{project_id_or_identifier}.json")
        return Project.from_api(data["project"])

    def add_issue_comment(self, issue_id: int, markdown: str) -> None:
        self.update_issue(issue_id, notes=markdown)

    def update_issue(
        self,
        issue_id: int,
        notes: str | None = None,
        status_id: int | None = None,
        done_ratio: int | None = None,
        priority_id: int | None = None,
    ) -> None:
        issue: dict[str, Any] = {}
        if notes is not None:
            issue["notes"] = notes
        if status_id is not None:
            issue["status_id"] = status_id
        if done_ratio is not None:
            issue["done_ratio"] = done_ratio
        if priority_id is not None:
            issue["priority_id"] = priority_id
        self._request("PUT", f"/issues/{issue_id}.json", json={"issue": issue})

    def get_issue_status_id_by_name(self, name: str) -> int:
        data = self._request("GET", "/issue_statuses.json")
        return self._find_id_by_name(data.get("issue_statuses", []), name, "issue status")

    def get_issue_priority_id_by_name(self, name: str) -> int:
        data = self._request("GET", "/enumerations/issue_priorities.json")
        return self._find_id_by_name(data.get("issue_priorities", []), name, "issue priority")

    def create_issue(
        self,
        project_id: int,
        subject: str,
        description: str,
        parent_issue_id: int | None = None,
        tracker_id: int | None = None,
        priority_id: int | None = None,
    ) -> int:
        issue: dict[str, Any] = {
            "project_id": project_id,
            "subject": subject,
            "description": description,
        }
        if parent_issue_id is not None:
            issue["parent_issue_id"] = parent_issue_id
        if tracker_id is not None:
            issue["tracker_id"] = tracker_id
        if priority_id is not None:
            issue["priority_id"] = priority_id
        data = self._request("POST", "/issues.json", json={"issue": issue})
        return int(data["issue"]["id"])

    def _find_id_by_name(self, items: list[dict[str, Any]], name: str, label: str) -> int:
        for item in items:
            if str(item.get("name", "")).lower() == name.lower():
                return int(item["id"])
        available = ", ".join(str(item.get("name", "")) for item in items)
        raise RedmineError(f"Redmine {label} not found by name {name!r}. Available: {available}")

    def list_open_assigned_issues(self, limit: int = 20) -> list[Issue]:
        data = self._request(
            "GET",
            "/issues.json",
            params={"assigned_to_id": "me", "status_id": "open", "limit": limit, "sort": "updated_on:desc"},
        )
        return [Issue.from_api(raw) for raw in data.get("issues", [])]

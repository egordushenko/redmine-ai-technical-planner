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
        self._request("PUT", f"/issues/{issue_id}.json", json={"issue": {"notes": markdown}})

    def list_open_assigned_issues(self, limit: int = 20) -> list[Issue]:
        data = self._request(
            "GET",
            "/issues.json",
            params={"assigned_to_id": "me", "status_id": "open", "limit": limit, "sort": "updated_on:desc"},
        )
        return [Issue.from_api(raw) for raw in data.get("issues", [])]

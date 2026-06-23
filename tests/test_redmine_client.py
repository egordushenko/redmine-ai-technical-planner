import json

import httpx
import pytest

from app.redmine.client import RedmineClient, RedmineError


def test_get_issue_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/issues/123.json"
        assert request.url.params["include"] == "journals,attachments,relations"
        assert request.headers["X-Redmine-API-Key"] == "secret"
        return httpx.Response(
            200,
            json={
                "issue": {
                    "id": 123,
                    "subject": "Fix login",
                    "project": {"id": 10, "name": "Demo", "identifier": "demo"},
                    "updated_on": "2026-06-22T10:00:00Z",
                }
            },
        )

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    issue = client.get_issue(123)

    assert issue.id == 123
    assert issue.project.identifier == "demo"


def test_get_project_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/projects/10.json"
        return httpx.Response(200, json={"project": {"id": 10, "name": "Demo", "identifier": "demo"}})

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    project = client.get_project(10)

    assert project.identifier == "demo"


def test_add_issue_comment_success():
    seen_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/issues/123.json"
        seen_payload.update(json.loads(request.content))
        return httpx.Response(204)

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    client.add_issue_comment(123, "hello")

    assert seen_payload == {"issue": {"notes": "hello"}}


def test_update_issue_with_notes_and_fields():
    seen_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path == "/issues/123.json"
        seen_payload.update(json.loads(request.content))
        return httpx.Response(204)

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    client.update_issue(123, notes="hello", status_id=2, done_ratio=50, priority_id=3)

    assert seen_payload == {"issue": {"notes": "hello", "status_id": 2, "done_ratio": 50, "priority_id": 3}}


def test_list_issue_statuses_and_priorities():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/issue_statuses.json":
            return httpx.Response(200, json={"issue_statuses": [{"id": 2, "name": "In Progress"}]})
        if request.url.path == "/enumerations/issue_priorities.json":
            return httpx.Response(200, json={"issue_priorities": [{"id": 3, "name": "High"}]})
        raise AssertionError(request.url.path)

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    assert client.get_issue_status_id_by_name("In Progress") == 2
    assert client.get_issue_priority_id_by_name("High") == 3


def test_create_issue_success():
    seen_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/issues.json"
        seen_payload.update(json.loads(request.content))
        return httpx.Response(201, json={"issue": {"id": 456}})

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    issue_id = client.create_issue(
        project_id=10,
        subject="AI plan: update controller",
        description="Generated subtask",
        parent_issue_id=123,
        tracker_id=1,
        priority_id=3,
    )

    assert issue_id == 456
    assert seen_payload == {
        "issue": {
            "project_id": 10,
            "subject": "AI plan: update controller",
            "description": "Generated subtask",
            "parent_issue_id": 123,
            "tracker_id": 1,
            "priority_id": 3,
        }
    }


def test_list_child_issues_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/issues.json"
        assert request.url.params["parent_id"] == "123"
        assert request.url.params["status_id"] == "*"
        return httpx.Response(
            200,
            json={
                "issues": [
                    {
                        "id": 456,
                        "subject": "Update controller",
                        "project": {"id": 10, "name": "Demo", "identifier": "demo"},
                        "updated_on": "2026-06-22T10:00:00Z",
                    }
                ]
            },
        )

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    issues = client.list_child_issues(123)

    assert len(issues) == 1
    assert issues[0].subject == "Update controller"


def test_redmine_error_handling():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"errors": ["boom"]})

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(RedmineError) as exc:
        client.get_issue(123)

    assert "500" in str(exc.value)

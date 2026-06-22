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


def test_redmine_error_handling():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"errors": ["boom"]})

    client = RedmineClient("https://redmine.test", "secret", http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(RedmineError) as exc:
        client.get_issue(123)

    assert "500" in str(exc.value)

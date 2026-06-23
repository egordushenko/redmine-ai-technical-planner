import json

import httpx

from app.llm.client import LLMClient


def _client_returning(*contents: str) -> LLMClient:
    responses = iter(contents)

    def handler(request: httpx.Request) -> httpx.Response:
        content = next(responses)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": content,
                        }
                    }
                ]
            },
        )

    return LLMClient(
        "https://llm.test/v1",
        "secret",
        "test-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_analyze_parses_fenced_json_without_repair():
    payload = {
        "task_understanding": "Add budget warnings.",
        "files_to_change": [
            {
                "path": "src/expense.py",
                "relevance_reason": "Creates expenses.",
                "suggested_changes": ["Check monthly limit."],
                "confidence": "high",
            }
        ],
        "implementation_plan": ["Add check."],
        "subtasks": ["Add repository query."],
        "effort_estimate": "2-4 hours.",
        "verification_steps": ["Run tests."],
        "risks": ["Session flush timing."],
        "analysis_limits": [],
    }
    client = _client_returning("```json\n" + json.dumps(payload) + "\n```")

    response = client.analyze("issue", "repo")

    assert response.result.structured
    assert response.result.task_understanding == "Add budget warnings."
    assert response.result.files_to_change[0].path == "src/expense.py"
    assert response.result.subtasks == ["Add repository query."]


def test_analyze_extracts_json_object_from_text():
    client = _client_returning(
        'Here is the plan:\n{"task_understanding":"Fix login","implementation_plan":["Patch callback"]}\nDone.'
    )

    response = client.analyze("issue", "repo")

    assert response.result.structured
    assert response.result.task_understanding == "Fix login"
    assert response.result.implementation_plan == ["Patch callback"]


def test_analyze_uses_robust_parser_after_repair():
    client = _client_returning(
        "not json",
        '```json\n{"task_understanding":"Fixed by repair","implementation_plan":["Step"]}\n```',
    )

    response = client.analyze("issue", "repo")

    assert response.result.structured
    assert response.result.task_understanding == "Fixed by repair"


def test_analyze_returns_unstructured_fallback_after_failed_repair():
    client = _client_returning("not json", "still not json")

    response = client.analyze("issue", "repo")

    assert not response.result.structured
    assert response.result.raw_text == "not json"
    assert "not json" not in response.result.task_understanding

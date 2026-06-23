from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any

import httpx

from app.llm.prompts import REPAIR_PROMPT_TEMPLATE, SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from app.llm.schemas import AnalysisResult


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class LLMResponse:
    result: AnalysisResult
    latency_seconds: float


class LLMClient:
    def __init__(self, base_url: str, api_key: str, model: str, http_client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = http_client or httpx.Client(timeout=120.0)

    def analyze(self, issue_context: str, repo_context: str) -> LLMResponse:
        prompt = USER_PROMPT_TEMPLATE.format(issue_context=issue_context, repo_context=repo_context)
        started = time.perf_counter()
        raw_text = self._chat(prompt)
        try:
            result = AnalysisResult.from_dict(_parse_json_object(raw_text))
        except (JSONDecodeError, ValueError, TypeError, KeyError, AttributeError):
            repaired = self._chat(REPAIR_PROMPT_TEMPLATE.format(raw_text=raw_text))
            try:
                result = AnalysisResult.from_dict(_parse_json_object(repaired))
            except (JSONDecodeError, ValueError, TypeError, KeyError, AttributeError):
                result = AnalysisResult(
                    task_understanding="Не удалось выполнить структурированный разбор ответа модели.",
                    files_to_change=[],
                    implementation_plan=[],
                    subtasks=[],
                    effort_estimate="Не удалось оценить: LLM вернул невалидный JSON.",
                    verification_steps=[],
                    risks=["LLM вернул невалидный JSON; опубликован fallback-комментарий."],
                    analysis_limits=["Структурированный разбор недоступен."],
                    raw_text=raw_text,
                    structured=False,
                )
        return LLMResponse(result=result, latency_seconds=time.perf_counter() - started)

    def _chat(self, user_prompt: str) -> str:
        response = self._client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
            },
        )
        if response.status_code >= 400:
            raise LLMError(f"LLM API error {response.status_code}: {response.text}")
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _parse_json_object(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise TypeError("LLM response content must be a string")
    candidates = _json_candidates(text)
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except JSONDecodeError as exc:
            last_error = exc
            continue
        if not isinstance(data, dict):
            raise ValueError("LLM JSON response must be an object")
        return data
    if last_error:
        raise last_error
    raise ValueError("No JSON object found in LLM response")


def _json_candidates(text: str) -> list[str]:
    stripped = text.strip().strip("`").strip()
    candidates: list[str] = []
    fence_matches = re.findall(r"```(?:json|JSON)?\s*(.*?)```", text, flags=re.DOTALL)
    candidates.extend(match.strip() for match in fence_matches if match.strip())
    if stripped:
        candidates.append(stripped)
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        candidates.append(text[first : last + 1].strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped

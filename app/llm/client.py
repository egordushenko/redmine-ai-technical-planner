from __future__ import annotations

import json
import time
from dataclasses import dataclass

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
            result = AnalysisResult.from_dict(json.loads(raw_text))
        except json.JSONDecodeError:
            repaired = self._chat(REPAIR_PROMPT_TEMPLATE.format(raw_text=raw_text))
            try:
                result = AnalysisResult.from_dict(json.loads(repaired))
            except json.JSONDecodeError:
                result = AnalysisResult(
                    task_understanding=raw_text,
                    files_to_change=[],
                    implementation_plan=[],
                    effort_estimate="Не удалось оценить: LLM вернул невалидный JSON.",
                    verification_steps=[],
                    risks=["LLM вернул невалидный JSON; опубликован raw fallback."],
                    analysis_limits=["Структурированный разбор недоступен."],
                    raw_text=raw_text,
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

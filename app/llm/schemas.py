from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Confidence = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class FileChangePlan:
    path: str
    relevance_reason: str
    suggested_changes: list[str]
    confidence: Confidence

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileChangePlan":
        if not isinstance(data, dict):
            data = {"path": "", "relevance_reason": "", "suggested_changes": [data], "confidence": "low"}
        confidence = data.get("confidence", "low")
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        changes = data.get("suggested_changes") or []
        if isinstance(changes, str):
            changes = [changes]
        elif not isinstance(changes, list):
            changes = [changes]
        return cls(
            path=str(data.get("path", "")),
            relevance_reason=str(data.get("relevance_reason", "")),
            suggested_changes=[str(item) for item in changes],
            confidence=confidence,
        )


@dataclass(frozen=True)
class AnalysisResult:
    task_understanding: str
    files_to_change: list[FileChangePlan] = field(default_factory=list)
    implementation_plan: list[str] = field(default_factory=list)
    subtasks: list[str] = field(default_factory=list)
    effort_estimate: str = ""
    verification_steps: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    analysis_limits: list[str] = field(default_factory=list)
    raw_text: str | None = None
    structured: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisResult":
        if not isinstance(data, dict):
            raise ValueError("analysis result must be a JSON object")

        def string_list(value: Any) -> list[str]:
            if value is None:
                return []
            if isinstance(value, list):
                return [str(item) for item in value if item is not None]
            if isinstance(value, str):
                return [value]
            return [str(value)]

        files = data.get("files_to_change") or []
        if isinstance(files, dict):
            files = [files]
        elif not isinstance(files, list):
            files = []

        return cls(
            task_understanding=str(data.get("task_understanding", "")),
            files_to_change=[FileChangePlan.from_dict(item) for item in files],
            implementation_plan=string_list(data.get("implementation_plan")),
            subtasks=string_list(data.get("subtasks")),
            effort_estimate=str(data.get("effort_estimate", "")),
            verification_steps=string_list(data.get("verification_steps")),
            risks=string_list(data.get("risks")),
            analysis_limits=string_list(data.get("analysis_limits")),
            structured=True,
        )

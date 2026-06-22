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
        confidence = data.get("confidence", "low")
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        changes = data.get("suggested_changes") or []
        if isinstance(changes, str):
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
    verification_steps: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    analysis_limits: list[str] = field(default_factory=list)
    raw_text: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalysisResult":
        return cls(
            task_understanding=str(data.get("task_understanding", "")),
            files_to_change=[FileChangePlan.from_dict(item) for item in data.get("files_to_change", [])],
            implementation_plan=[str(item) for item in data.get("implementation_plan", [])],
            verification_steps=[str(item) for item in data.get("verification_steps", [])],
            risks=[str(item) for item in data.get("risks", [])],
            analysis_limits=[str(item) for item in data.get("analysis_limits", [])],
        )

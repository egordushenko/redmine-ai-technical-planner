from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Project:
    id: int | None = None
    name: str = ""
    identifier: str | None = None

    @classmethod
    def from_api(cls, data: dict[str, Any] | None) -> "Project":
        data = data or {}
        return cls(id=data.get("id"), name=data.get("name", ""), identifier=data.get("identifier"))


@dataclass(frozen=True)
class Issue:
    id: int
    subject: str
    project: Project
    description: str = ""
    updated_on: str = ""
    status: dict[str, Any] | None = None
    tracker: dict[str, Any] | None = None
    priority: dict[str, Any] | None = None
    assigned_to: dict[str, Any] | None = None
    created_on: str = ""
    journals: list[dict[str, Any]] = field(default_factory=list)
    attachments: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Issue":
        return cls(
            id=int(data["id"]),
            subject=data.get("subject", ""),
            description=data.get("description") or "",
            project=Project.from_api(data.get("project")),
            updated_on=data.get("updated_on", ""),
            status=data.get("status"),
            tracker=data.get("tracker"),
            priority=data.get("priority"),
            assigned_to=data.get("assigned_to"),
            created_on=data.get("created_on", ""),
            journals=data.get("journals") or [],
            attachments=data.get("attachments") or [],
            relations=data.get("relations") or [],
        )

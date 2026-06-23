from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.code_index.search import FileScore
from app.code_index.scanner import collect_important_files
from app.redmine.models import Issue


@dataclass(frozen=True)
class FileContext:
    path: str
    content: str


def build_file_context(path: Path, keywords: list[str], max_chars_per_file: int) -> FileContext:
    content = path.read_text(encoding="utf-8", errors="replace")
    if len(content) <= max_chars_per_file:
        return FileContext(path=path.as_posix(), content=content)
    lower = content.lower()
    positions = [lower.find(keyword.lower()) for keyword in keywords if keyword and lower.find(keyword.lower()) >= 0]
    center = positions[0] if positions else 0
    start = max(0, center - max_chars_per_file // 2)
    end = min(len(content), start + max_chars_per_file)
    return FileContext(path=path.as_posix(), content=content[start:end])


def build_issue_context(issue: Issue) -> str:
    comments = [str(item.get("notes", "")).strip() for item in issue.journals[-5:] if item.get("notes")]
    attachments = [str(item.get("filename")) for item in issue.attachments if item.get("filename")]
    return "\n".join(
        [
            f"ID: {issue.id}",
            f"Subject: {issue.subject}",
            f"Description: {issue.description}",
            "Recent comments:",
            "\n---\n".join(comments),
            f"Attachments: {', '.join(attachments)}",
        ]
    )


def build_repo_context(
    repo_path: Path,
    repo_tree: str,
    selected_files: list[FileScore],
    keywords: list[str],
    max_chars_per_file: int,
    max_total_context_chars: int,
) -> str:
    parts: list[str] = []
    remaining = max_total_context_chars
    truncated = False

    def append_part(part: str) -> bool:
        nonlocal remaining, truncated
        separator_len = 1 if parts else 0
        needed = len(part) + separator_len
        if needed <= remaining:
            parts.append(part)
            remaining -= needed
            return True
        marker = "...[truncated due to context budget]"
        available = max(0, remaining - separator_len - len(marker))
        if available > 0:
            parts.append(part[:available] + marker)
        elif remaining >= len(marker) + separator_len:
            parts.append(marker)
        truncated = True
        remaining = 0
        return False

    for part in ("<repo_summary>", repo_tree, "</repo_summary>"):
        if not append_part(part):
            return "\n".join(parts)
    important = collect_important_files(repo_path)
    if important:
        if not append_part("<important_files>"):
            return "\n".join(parts)
        for path, content in important.items():
            if not append_part(f"File: {path}\n```text\n{content}\n```"):
                return "\n".join(parts)
        if not append_part("</important_files>"):
            return "\n".join(parts)
    if not append_part("<candidate_files>"):
        return "\n".join(parts)
    for item in selected_files:
        file_context = build_file_context(item.source_file.path, keywords, max_chars_per_file)
        language = item.source_file.path.suffix.lstrip(".") or "text"
        reasons = "; ".join(item.reasons[:5])
        if not append_part(
            "\n".join(
                [
                    f"File: {item.relative_path}",
                    f"Reason selected: {reasons}",
                    f"Score: {item.score}",
                    f"Matched lines: {', '.join(map(str, item.matches)) if item.matches else 'n/a'}",
                    f"```{language}",
                    file_context.content,
                    "```",
                ]
            )
        ):
            return "\n".join(parts)
    if not truncated:
        append_part("</candidate_files>")
    return "\n".join(parts)

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
    parts: list[str] = ["<repo_summary>", repo_tree, "</repo_summary>"]
    important = collect_important_files(repo_path)
    if important:
        parts.append("<important_files>")
        for path, content in important.items():
            parts.append(f"File: {path}\n```text\n{content}\n```")
        parts.append("</important_files>")
    parts.append("<candidate_files>")
    for item in selected_files:
        file_context = build_file_context(item.source_file.path, keywords, max_chars_per_file)
        language = item.source_file.path.suffix.lstrip(".") or "text"
        reasons = "; ".join(item.reasons[:5])
        parts.append(
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
        )
    parts.append("</candidate_files>")
    context = "\n".join(parts)
    return context[:max_total_context_chars]

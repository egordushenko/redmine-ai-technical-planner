from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from app.code_index.scanner import SourceFile
from app.redmine.models import Issue


STOP_WORDS = {
    "and",
    "the",
    "for",
    "with",
    "что",
    "как",
    "при",
    "для",
    "это",
    "нужно",
    "надо",
    "если",
}


@dataclass(frozen=True)
class FileScore:
    source_file: SourceFile
    score: int
    matches: list[int] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def relative_path(self) -> str:
        return self.source_file.relative_path


def extract_keywords(issue: Issue) -> list[str]:
    chunks = [issue.subject, issue.description]
    chunks.extend(str(item.get("notes", "")) for item in issue.journals[-5:] if item.get("notes"))
    chunks.extend(str(item.get("filename", "")) for item in issue.attachments if item.get("filename"))
    text = "\n".join(chunks)
    keywords: list[str] = []
    keywords.extend(match.group(1).strip() for match in re.finditer(r'"([^"]{3,80})"', text))
    keywords.extend(match.group(0).strip("/").replace("/", "/") for match in re.finditer(r"/[A-Za-z0-9_./-]{2,}", text))
    for token in re.findall(r"[A-Za-zА-Яа-я0-9_][A-Za-zА-Яа-я0-9_-]{2,}", text):
        normalized = token.strip("_-")
        if normalized and normalized.lower() not in STOP_WORDS:
            keywords.append(normalized)
    deduped: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        key = keyword.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(keyword)
    return deduped[:40]


def score_files(issue: Issue, files: list[SourceFile], repo_path: Path | str) -> list[FileScore]:
    keywords = extract_keywords(issue)
    scored: list[FileScore] = []
    for source_file in files:
        score = 0
        matches: list[int] = []
        reasons: list[str] = []
        path_lower = source_file.relative_path.lower()
        filename_lower = Path(source_file.relative_path).name.lower()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in filename_lower:
                score += 10
                reasons.append(f"keyword in filename: {keyword}")
            elif keyword_lower in path_lower:
                score += 7
                reasons.append(f"keyword in path: {keyword}")
        try:
            content = source_file.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        content_lower = content.lower()
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower and keyword_lower in content_lower:
                score += 5
                reasons.append(f"keyword in content: {keyword}")
                for idx, line in enumerate(content.splitlines(), start=1):
                    if keyword_lower in line.lower():
                        matches.append(idx)
                        break
        if any(part in path_lower for part in ("route", "controller", "service", "model", "test")):
            score += 2
        if source_file.size > 250_000:
            score -= 5
        if score > 0:
            scored.append(FileScore(source_file=source_file, score=score, matches=sorted(set(matches)), reasons=reasons))
    return sorted(scored, key=lambda item: (-item.score, item.relative_path))

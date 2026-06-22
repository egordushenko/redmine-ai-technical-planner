from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".cache",
    ".idea",
    ".vscode",
    ".next",
    ".nuxt",
    "target",
    "vendor",
}
EXCLUDED_FILENAMES = {
    ".env",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
}
EXCLUDED_SUFFIXES = {
    ".lock",
    ".min.js",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".mp4",
    ".mov",
    ".mp3",
}
ALLOWED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".vue",
    ".go",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".cs",
    ".rs",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".md",
}
IMPORTANT_FILES = [
    "README.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "docker-compose.yml",
    "Dockerfile",
    ".env.example",
]
SENSITIVE_PATTERNS = ("PRIVATE KEY", "API_KEY", "SECRET", "PASSWORD", "TOKEN")


@dataclass(frozen=True)
class SourceFile:
    path: Path
    relative_path: str
    size: int


def is_sensitive_path(path: Path) -> bool:
    if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
        return True
    text = str(path).upper()
    return any(pattern.upper() in text for pattern in SENSITIVE_PATTERNS)


def should_skip_path(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
        return True
    name = path.name
    if name in EXCLUDED_FILENAMES or name.startswith(".env."):
        return True
    return any(name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES)


def list_source_files(repo_path: Path | str) -> list[SourceFile]:
    root = Path(repo_path)
    files: list[SourceFile] = []
    for path in root.rglob("*"):
        if not path.is_file() or should_skip_path(path, root) or is_sensitive_path(path):
            continue
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            continue
        files.append(SourceFile(path=path, relative_path=path.relative_to(root).as_posix(), size=path.stat().st_size))
    return sorted(files, key=lambda item: item.relative_path)


def build_repo_tree(repo_path: Path | str, max_lines: int = 300) -> str:
    root = Path(repo_path)
    lines: list[str] = [f"{root.name}/"]
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path == root or should_skip_path(path, root):
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        depth = len(relative.parts)
        suffix = "/" if path.is_dir() else ""
        lines.append(f"{'  ' * depth}{path.name}{suffix}")
        if len(lines) >= max_lines:
            lines.append("...")
            break
    return "\n".join(lines)


def collect_important_files(repo_path: Path | str, max_chars: int = 12000) -> dict[str, str]:
    root = Path(repo_path)
    collected: dict[str, str] = {}
    for name in IMPORTANT_FILES:
        path = root / name
        if not path.is_file() or is_sensitive_path(path):
            continue
        collected[name] = path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    return collected

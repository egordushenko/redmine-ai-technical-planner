from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    redmine_base_url: str
    redmine_api_key: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    repos_base_dir: Path
    bot_signature: str
    max_files_to_analyze: int
    max_chars_per_file: int
    max_total_context_chars: int
    state_db_path: Path
    log_level: str
    projects_yaml_path: Path
    post_errors_to_redmine: bool


def load_settings(env_path: Path | str = ".env") -> Settings:
    _load_env_file(Path(env_path))
    return Settings(
        redmine_base_url=os.getenv("REDMINE_BASE_URL", "").rstrip("/"),
        redmine_api_key=os.getenv("REDMINE_API_KEY", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4.1-mini"),
        repos_base_dir=Path(os.getenv("REPOS_BASE_DIR", "./repos")),
        bot_signature=os.getenv("BOT_SIGNATURE", "AI technical planner bot"),
        max_files_to_analyze=int(os.getenv("MAX_FILES_TO_ANALYZE", "12")),
        max_chars_per_file=int(os.getenv("MAX_CHARS_PER_FILE", "12000")),
        max_total_context_chars=int(os.getenv("MAX_TOTAL_CONTEXT_CHARS", "80000")),
        state_db_path=Path(os.getenv("STATE_DB_PATH", "./data/state.sqlite3")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        projects_yaml_path=Path(os.getenv("PROJECTS_YAML_PATH", "./projects.yaml")),
        post_errors_to_redmine=_bool_env("POST_ERRORS_TO_REDMINE", False),
    )

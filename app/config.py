from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PLACEHOLDER_VALUES = {"", "replace_me", "your_key_here", "changeme", "todo"}


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


def _env_value(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    if value.lower() in PLACEHOLDER_VALUES:
        return ""
    return value


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
    redmine_update_issue_after_plan: bool
    redmine_after_plan_status_name: str
    redmine_after_plan_priority_name: str
    redmine_after_plan_done_ratio: int
    redmine_create_subtasks_after_plan: bool


def load_settings(env_path: Path | str = ".env") -> Settings:
    _load_env_file(Path(env_path))
    openrouter_api_key = _env_value("OPENROUTER_API_KEY")
    generic_llm_api_key = _env_value("LLM_API_KEY")
    return Settings(
        redmine_base_url=_env_value("REDMINE_BASE_URL").rstrip("/"),
        redmine_api_key=_env_value("REDMINE_API_KEY"),
        llm_base_url=_env_value("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/"),
        llm_api_key=openrouter_api_key or generic_llm_api_key,
        llm_model=_env_value("LLM_MODEL", "openai/gpt-4.1-mini"),
        repos_base_dir=Path(os.getenv("REPOS_BASE_DIR", "./repos")),
        bot_signature=os.getenv("BOT_SIGNATURE", "AI technical planner bot"),
        max_files_to_analyze=int(os.getenv("MAX_FILES_TO_ANALYZE", "12")),
        max_chars_per_file=int(os.getenv("MAX_CHARS_PER_FILE", "12000")),
        max_total_context_chars=int(os.getenv("MAX_TOTAL_CONTEXT_CHARS", "80000")),
        state_db_path=Path(os.getenv("STATE_DB_PATH", "./data/state.sqlite3")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        projects_yaml_path=Path(os.getenv("PROJECTS_YAML_PATH", "./projects.yaml")),
        post_errors_to_redmine=_bool_env("POST_ERRORS_TO_REDMINE", False),
        redmine_update_issue_after_plan=_bool_env("REDMINE_UPDATE_ISSUE_AFTER_PLAN", False),
        redmine_after_plan_status_name=os.getenv("REDMINE_AFTER_PLAN_STATUS_NAME", "In Progress"),
        redmine_after_plan_priority_name=os.getenv("REDMINE_AFTER_PLAN_PRIORITY_NAME", "High"),
        redmine_after_plan_done_ratio=int(os.getenv("REDMINE_AFTER_PLAN_DONE_RATIO", "50")),
        redmine_create_subtasks_after_plan=_bool_env("REDMINE_CREATE_SUBTASKS_AFTER_PLAN", False),
    )


def validate_settings(settings: Settings) -> list[str]:
    errors: list[str] = []
    if not settings.redmine_base_url:
        errors.append("REDMINE_BASE_URL is required.")
    if not settings.redmine_api_key:
        errors.append("REDMINE_API_KEY is required and must not be a placeholder.")
    if not settings.llm_api_key:
        errors.append("OPENROUTER_API_KEY is required for the default setup; LLM_API_KEY may be used as a generic fallback.")
    if not settings.projects_yaml_path.exists():
        errors.append(f"projects.yaml not found: {settings.projects_yaml_path}")
    if settings.max_files_to_analyze <= 0:
        errors.append("MAX_FILES_TO_ANALYZE must be greater than 0.")
    if settings.max_chars_per_file <= 0:
        errors.append("MAX_CHARS_PER_FILE must be greater than 0.")
    if settings.max_total_context_chars <= 0:
        errors.append("MAX_TOTAL_CONTEXT_CHARS must be greater than 0.")
    if settings.redmine_after_plan_done_ratio < 0 or settings.redmine_after_plan_done_ratio > 100:
        errors.append("REDMINE_AFTER_PLAN_DONE_RATIO must be between 0 and 100.")
    return errors

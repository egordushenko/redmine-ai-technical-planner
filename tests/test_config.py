from pathlib import Path

from app.config import load_settings


def test_load_settings_accepts_openrouter_api_key_alias(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "LLM_BASE_URL=https://openrouter.ai/api/v1",
                "OPENROUTER_API_KEY=sk-test",
                "LLM_MODEL=deepseek/deepseek-v4-flash",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(env_path)

    assert settings.llm_api_key == "sk-test"


def test_load_settings_reads_post_plan_issue_update_fields(tmp_path: Path, monkeypatch):
    for key in (
        "REDMINE_AFTER_PLAN_STATUS_NAME",
        "REDMINE_AFTER_PLAN_PRIORITY_NAME",
        "REDMINE_AFTER_PLAN_DONE_RATIO",
        "REDMINE_UPDATE_ISSUE_AFTER_PLAN",
        "REDMINE_CREATE_SUBTASKS_AFTER_PLAN",
    ):
        monkeypatch.delenv(key, raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "REDMINE_UPDATE_ISSUE_AFTER_PLAN=true",
                "REDMINE_AFTER_PLAN_STATUS_NAME=In Progress",
                "REDMINE_AFTER_PLAN_PRIORITY_NAME=High",
                "REDMINE_AFTER_PLAN_DONE_RATIO=50",
                "REDMINE_CREATE_SUBTASKS_AFTER_PLAN=true",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_settings(env_path)

    assert settings.redmine_update_issue_after_plan
    assert settings.redmine_after_plan_status_name == "In Progress"
    assert settings.redmine_after_plan_priority_name == "High"
    assert settings.redmine_after_plan_done_ratio == 50
    assert settings.redmine_create_subtasks_after_plan

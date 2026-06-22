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

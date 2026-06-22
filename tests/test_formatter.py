from app.llm.schemas import AnalysisResult, FileChangePlan
from app.planner.formatter import format_error_comment, format_success_comment


def test_formats_markdown_comment():
    result = AnalysisResult(
        task_understanding="Нужно исправить авторизацию.",
        files_to_change=[
            FileChangePlan(
                path="src/auth.py",
                relevance_reason="Содержит проверку сессии.",
                suggested_changes=["Добавить redirect target."],
                confidence="high",
            )
        ],
        implementation_plan=["Проверить middleware.", "Добавить тест."],
        effort_estimate="2-4 часа на реализацию и проверку.",
        verification_steps=["Проверить login flow."],
        risks=["Неясен формат сессии."],
        analysis_limits=["Агент не выполнял код."],
    )

    comment = format_success_comment(result, model_name="gpt-test", timestamp="2026-06-22T12:00:00Z")

    assert "🤖 **AI technical plan**" in comment
    assert "**Модель:** `gpt-test`" in comment
    assert "`src/auth.py`" in comment
    assert "Уверенность: high" in comment
    assert "### 4. Оценка временных затрат" in comment
    assert "2-4 часа" in comment


def test_handles_empty_files_to_change():
    result = AnalysisResult(
        task_understanding="Недостаточно данных.",
        files_to_change=[],
        implementation_plan=[],
        verification_steps=[],
        risks=[],
        analysis_limits=[],
    )

    comment = format_success_comment(result, model_name="gpt-test", timestamp="2026-06-22T12:00:00Z")

    assert "Не удалось уверенно определить файлы для изменения." in comment


def test_formats_error_comment():
    comment = format_error_comment("missing mapping", "Добавьте projects.yaml")

    assert "Не удалось выполнить анализ." in comment
    assert "missing mapping" in comment


def test_strips_model_numbering_from_lists():
    result = AnalysisResult(
        task_understanding="Нужно исправить фильтр.",
        files_to_change=[],
        implementation_plan=["1. Добавить scope.", "2) Обновить view."],
        effort_estimate="1 день.",
        verification_steps=["1. Проверить список."],
        risks=["1. Возможен конфликт фильтров."],
        analysis_limits=["1. Агент не выполнял код."],
    )

    comment = format_success_comment(result, model_name="gpt-test", timestamp="2026-06-22T12:00:00Z")

    assert "1. 1." not in comment
    assert "- 1." not in comment

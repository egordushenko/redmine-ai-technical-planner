from __future__ import annotations

from app.llm.schemas import AnalysisResult, FileChangePlan


def _list_items(items: list[str], empty: str = "- Не указано.") -> str:
    if not items:
        return empty
    return "\n".join(f"{idx}. {item}" for idx, item in enumerate(items, start=1))


def _bullet_items(items: list[str], empty: str = "- Не указано.") -> str:
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def _format_file(item: FileChangePlan, index: int) -> str:
    changes = "\n".join(f"     - {change}" for change in item.suggested_changes) or "     - Не указано."
    return "\n".join(
        [
            f"{index}. `{item.path}`",
            f"   - Почему релевантен: {item.relevance_reason}",
            "   - Что изменить:",
            changes,
            f"   - Уверенность: {item.confidence}",
        ]
    )


def format_success_comment(result: AnalysisResult, model_name: str, timestamp: str) -> str:
    if result.files_to_change:
        files = "\n".join(_format_file(item, idx) for idx, item in enumerate(result.files_to_change, start=1))
    else:
        files = "Не удалось уверенно определить файлы для изменения."
    return "\n\n".join(
        [
            "🤖 **AI technical plan**",
            f"**Статус анализа:** успешно  \n**Модель:** `{model_name}`  \n**Дата:** `{timestamp}`",
            f"### 1. Краткое понимание задачи\n{result.task_understanding or 'Не указано.'}",
            f"### 2. Предполагаемые файлы для изменения\n{files}",
            f"### 3. План реализации\n{_list_items(result.implementation_plan)}",
            f"### 4. Что проверить после изменений\n{_bullet_items(result.verification_steps)}",
            f"### 5. Риски и неопределённости\n{_bullet_items(result.risks)}",
            f"### 6. Ограничения анализа\n{_bullet_items(result.analysis_limits)}",
            "---\n_Комментарий создан автоматически. Агент не изменял код и не выполнял тесты._",
        ]
    )


def format_error_comment(reason: str, action: str = "Проверьте конфигурацию и повторите анализ.") -> str:
    return "\n\n".join(
        [
            "🤖 **AI technical plan**",
            "Не удалось выполнить анализ.",
            f"Причина: {reason}",
            f"Что можно сделать: {action}",
        ]
    )

from app.llm.schemas import AnalysisResult


def test_analysis_result_parses_effort_estimate():
    result = AnalysisResult.from_dict(
        {
            "task_understanding": "Нужно добавить фильтр.",
            "files_to_change": [],
            "implementation_plan": [],
            "effort_estimate": "2-4 часа.",
            "verification_steps": [],
            "risks": [],
            "analysis_limits": [],
        }
    )

    assert result.effort_estimate == "2-4 часа."

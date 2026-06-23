from pathlib import Path

from app.code_index.context_builder import build_repo_context
from app.code_index.scanner import SourceFile
from app.code_index.search import FileScore


def test_build_repo_context_adds_truncation_marker_when_budget_is_exhausted(tmp_path: Path):
    source = tmp_path / "src" / "large.py"
    source.parent.mkdir()
    source.write_text("x = 1\n" * 1000, encoding="utf-8")
    selected = [
        FileScore(
            source_file=SourceFile(source, "src/large.py", source.stat().st_size),
            score=10,
            reasons=["large"],
        )
    ]

    context = build_repo_context(
        tmp_path,
        repo_tree="demo/\n  src/\n    large.py",
        selected_files=selected,
        keywords=[],
        max_chars_per_file=10_000,
        max_total_context_chars=250,
    )

    assert len(context) <= 250
    assert "...[truncated due to context budget]" in context

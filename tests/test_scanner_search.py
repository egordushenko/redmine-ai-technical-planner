from pathlib import Path

from app.code_index.context_builder import build_file_context
from app.code_index.scanner import build_repo_tree, collect_important_files, list_source_files
from app.code_index.search import extract_keywords, score_files
from app.redmine.models import Issue, Project


def _issue(subject: str, description: str = "") -> Issue:
    return Issue(
        id=1,
        subject=subject,
        description=description,
        project=Project(id=1, name="Demo", identifier="demo"),
        updated_on="2026-06-22T10:00:00Z",
    )


def test_excludes_node_modules_and_env_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "lib.js").write_text("x\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=secret\n", encoding="utf-8")

    files = list_source_files(tmp_path)

    assert [f.relative_path for f in files] == ["src/app.py"]


def test_detects_candidate_by_filename(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "payment_service.py").write_text("class Service: pass\n", encoding="utf-8")
    files = list_source_files(tmp_path)

    scored = score_files(_issue("payment fails"), files, tmp_path)

    assert scored[0].relative_path == "src/payment_service.py"
    assert scored[0].score >= 10


def test_detects_candidate_by_content(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("def login_user():\n    return True\n", encoding="utf-8")
    files = list_source_files(tmp_path)

    scored = score_files(_issue("login broken"), files, tmp_path)

    assert scored[0].relative_path == "src/service.py"
    assert scored[0].matches


def test_limits_large_file_context(tmp_path: Path):
    path = tmp_path / "large.py"
    path.write_text("\n".join([f"line {i}" for i in range(500)]) + "\nneedle\n", encoding="utf-8")

    context = build_file_context(path, ["needle"], max_chars_per_file=300)

    assert "needle" in context.content
    assert len(context.content) <= 300


def test_collects_repo_summary_inputs(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name":"demo"}\n', encoding="utf-8")
    (tmp_path / ".env.example").write_text("TOKEN=replace_me\n", encoding="utf-8")

    tree = build_repo_tree(tmp_path)
    important = collect_important_files(tmp_path)

    assert "README.md" in tree
    assert set(important) == {"README.md", "package.json", ".env.example"}


def test_extract_keywords_from_issue_fields():
    issue = _issue('Fix "redirect URL" in auth', "Login button fails at /login/callback")

    keywords = extract_keywords(issue)

    assert "redirect URL" in keywords
    assert "login/callback" in keywords
    assert "auth" in keywords

from __future__ import annotations

import argparse
import sys

from app.config import load_settings, validate_settings
from app.git.repo_manager import RepoManager
from app.llm.client import LLMClient
from app.planner.analyzer import Analyzer
from app.redmine.client import RedmineClient
from app.storage.state import StateStore
from app.utils.logging import configure_logging


def build_analyzer() -> Analyzer:
    settings = load_settings()
    errors = validate_settings(settings)
    if errors:
        raise SystemExit("Configuration error:\n- " + "\n- ".join(errors))
    configure_logging(settings.log_level)
    return Analyzer(
        settings=settings,
        redmine_client=RedmineClient(settings.redmine_base_url, settings.redmine_api_key),
        repo_manager=RepoManager(settings.projects_yaml_path, settings.repos_base_dir),
        llm_client=LLMClient(settings.llm_base_url, settings.llm_api_key, settings.llm_model),
        state_store=StateStore(settings.state_db_path),
    )


def cmd_analyze(args: argparse.Namespace) -> int:
    output = build_analyzer().analyze_issue(args.issue_id, dry_run=args.dry_run)
    if args.dry_run:
        print(output.markdown)
    elif output.skipped:
        print(f"Issue {args.issue_id} was already processed and has not changed.")
    else:
        print(f"Posted AI technical plan to issue {args.issue_id}.")
    return 0


def cmd_poll(args: argparse.Namespace) -> int:
    analyzer = build_analyzer()
    issues = analyzer.redmine_client.list_open_assigned_issues(limit=args.limit)
    for issue in issues:
        analyzer.analyze_issue(issue.id, dry_run=args.dry_run)
    print(f"Processed {len(issues)} issue(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="redmine-ai-technical-planner")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Analyze a single Redmine issue")
    analyze.add_argument("--issue-id", type=int, required=True)
    analyze.add_argument("--dry-run", action="store_true")
    analyze.set_defaults(func=cmd_analyze)
    poll = subparsers.add_parser("poll", help="Analyze open issues assigned to the bot user")
    poll.add_argument("--limit", type=int, default=20)
    poll.add_argument("--dry-run", action="store_true")
    poll.set_defaults(func=cmd_poll)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

# Redmine AI Technical Planner

## What It Does

CLI-agent for Redmine issues. It reads a Redmine issue, resolves its project to a Git repository through `projects.yaml`, updates the local checkout, selects likely relevant files, asks an OpenAI-compatible LLM for a technical plan, and posts that plan back to the same Redmine issue.

The agent only prepares a plan for a human developer. It does not edit the target repository, create branches, run tests in the target project, or open pull requests.
Optionally, after posting the plan, it can update the Redmine issue status, progress, priority, estimated time, and create Redmine child issues from the generated subtasks.

## Demo

This repository includes a local Redmine demo that shows the full MVP workflow:

1. A Redmine issue describes a feature request.
2. The agent reads the issue through the Redmine REST API.
3. It maps the Redmine project to a Git repository through `projects.yaml`.
4. It scans the repository and sends only selected context to the LLM.
5. It posts a technical implementation plan back to the same Redmine issue.
6. In the demo configuration, it moves the issue to `In Progress`, sets progress to `50%`, raises priority to `High`, fills estimated time, and creates child issues from the generated subtasks.

Recommended portfolio assets:

- `docs/assets/01-redmine-issue-before.png`: Redmine issue before running the agent.
- `docs/assets/02-cli-run.png`: CLI execution.
- `docs/assets/03-redmine-issue-after.png`: Redmine issue after analysis with updated status, priority, progress, estimated time, and child issues.
- `docs/assets/04-redmine-ai-comment-1.png`: first part of the generated AI technical plan.
- `docs/assets/05-redmine-ai-comment-2.png`: second part of the generated AI technical plan.

See [docs/demo.md](docs/demo.md) for the capture checklist and demo script.

## MVP Limitations

- No embeddings or vector database.
- No web UI.
- No automatic code changes.
- No deep AST analysis.
- Polling mode is intentionally minimal.
- The LLM receives only selected repository context, not the whole repository.

## Setup

```powershell
cp .env.example .env
cp projects.yaml.example projects.yaml
pip install -r requirements.txt
```

Edit `.env` and `projects.yaml` before running against a real Redmine instance.

## .env Configuration

- `REDMINE_BASE_URL`: Redmine base URL.
- `REDMINE_API_KEY`: Redmine API key for the bot user.
- `LLM_BASE_URL`: OpenAI-compatible API base URL.
- `OPENROUTER_API_KEY`: primary LLM API key for the default OpenRouter setup.
- `LLM_API_KEY`: optional generic fallback key for another OpenAI-compatible provider.
- `LLM_MODEL`: model name.
- `REPOS_BASE_DIR`: directory for local repository checkouts.
- `MAX_FILES_TO_ANALYZE`: candidate files sent to the LLM.
- `MAX_CHARS_PER_FILE`: per-file context cap.
- `MAX_TOTAL_CONTEXT_CHARS`: total repository context cap.
- `STATE_DB_PATH`: SQLite state path.
- `POST_ERRORS_TO_REDMINE`: whether analysis errors should be posted to Redmine.
- `REDMINE_UPDATE_ISSUE_AFTER_PLAN`: whether successful analysis should update status, progress, priority, and estimated time.
- `REDMINE_AFTER_PLAN_STATUS_NAME`: status name to set after posting the plan, for example `In Progress`.
- `REDMINE_AFTER_PLAN_PRIORITY_NAME`: priority name to set after posting the plan, for example `High`.
- `REDMINE_AFTER_PLAN_DONE_RATIO`: progress percentage to set after posting the plan, for example `50`.
- `REDMINE_CREATE_SUBTASKS_AFTER_PLAN`: whether generated subtasks should be created as Redmine child issues.

## projects.yaml Configuration

```yaml
projects:
  demo_project:
    repo_url: "git@github.com:company/demo-project.git"
    branch: "main"
    local_dir: "demo-project"
```

The key under `projects` must match Redmine `project.identifier`.

## LLM Provider

OpenRouter is the default provider in this MVP:

```env
LLM_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=replace_me
LLM_MODEL=openai/gpt-4.1-mini
```

`OPENROUTER_API_KEY` is used first. `LLM_API_KEY` is only a generic fallback for another OpenAI-compatible provider.

## Run Single Issue Analysis

```powershell
python -m app.main analyze --issue-id 1234
```

## Dry Run

```powershell
python -m app.main analyze --issue-id 1234 --dry-run
```

Dry-run prints Markdown to the console and does not post a Redmine comment.

On Windows PowerShell, switch the console to UTF-8 first if Russian text is displayed as mojibake:

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
```

## Polling Mode

```powershell
python -m app.main poll
```

Polling reads open issues assigned to the Redmine API user and processes them one by one.

## Local Redmine Demo

For a local portfolio demo, start Redmine with Docker:

```powershell
docker compose -f docker-compose.redmine.yml up -d
```

Then bootstrap a demo project and issue inside the container:

```powershell
docker cp scripts/bootstrap_redmine_demo.rb redmine-ai-planner-app:/tmp/bootstrap_redmine_demo.rb
docker exec redmine-ai-planner-app bash -lc "bundle exec rails runner /tmp/bootstrap_redmine_demo.rb"
```

The bootstrap creates project `BudgetBot` with identifier `budgetbot` and a sample issue. It writes the Redmine API key into the container file volume; do not print that key in logs or commits.
The generated API key belongs to the demo user `ai_planner_bot`, so comments are posted by the bot user rather than the admin account.

Run the real demo flow:

```powershell
chcp 65001
$env:PYTHONIOENCODING="utf-8"
python -m app.main analyze --issue-id 1
```

Then open `http://localhost:3000/issues/1` and check the generated comment.
With demo workflow flags enabled, the issue should also move to `In Progress`, show `50%` progress, use `High` priority, fill estimated time, and contain generated child issues.

## Security Notes

- Issue text is treated as untrusted input.
- Secret-like files such as `.env`, private keys, token files, lock files, and binary assets are excluded from LLM context.
- API keys and tokens are not logged intentionally.
- By default, the agent only adds Redmine `notes`.
- Status, progress, priority, estimated time, and child issue creation are enabled only through explicit env flags.
- The agent does not edit code, create branches, create commits, or open pull requests.

## Development

```powershell
pip install -r requirements.txt
```

## Tests

```powershell
pytest
ruff check .
```

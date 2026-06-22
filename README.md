# Redmine AI Technical Planner

## What It Does

CLI-agent for Redmine issues. It reads a Redmine issue, resolves its project to a Git repository through `projects.yaml`, updates the local checkout, selects likely relevant files, asks an OpenAI-compatible LLM for a technical plan, and posts that plan back to the same Redmine issue.

The agent only prepares a plan for a human developer. It does not edit the target repository, create branches, run tests in the target project, or open pull requests.

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
- `LLM_API_KEY`: LLM API key.
- `LLM_MODEL`: model name.
- `REPOS_BASE_DIR`: directory for local repository checkouts.
- `MAX_FILES_TO_ANALYZE`: candidate files sent to the LLM.
- `MAX_CHARS_PER_FILE`: per-file context cap.
- `MAX_TOTAL_CONTEXT_CHARS`: total repository context cap.
- `STATE_DB_PATH`: SQLite state path.
- `POST_ERRORS_TO_REDMINE`: whether analysis errors should be posted to Redmine.

## projects.yaml Configuration

```yaml
projects:
  demo_project:
    repo_url: "git@github.com:company/demo-project.git"
    branch: "main"
    local_dir: "demo-project"
```

The key under `projects` must match Redmine `project.identifier`.

## Run Single Issue Analysis

```powershell
python -m app.main analyze --issue-id 1234
```

## Dry Run

```powershell
python -m app.main analyze --issue-id 1234 --dry-run
```

Dry-run prints Markdown to the console and does not post a Redmine comment.

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

## Security Notes

- Issue text is treated as untrusted input.
- Secret-like files such as `.env`, private keys, token files, lock files, and binary assets are excluded from LLM context.
- API keys and tokens are not logged intentionally.
- Redmine updates only add `notes`; status, assignee, tracker, and priority are not changed.

## Development

```powershell
pip install -r requirements.txt
```

## Tests

```powershell
pytest
ruff check .
```

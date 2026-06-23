# Demo Walkthrough

This walkthrough is for a portfolio demo of Redmine AI Technical Planner. It uses a local Redmine instance and a demo GitHub repository, so no client data is required.

## Scenario

A developer receives a Redmine issue asking to add a category filter to the BudgetBot transaction list. Instead of manually searching the codebase first, they run the agent. The agent reads the issue, inspects the mapped repository, selects likely files, and posts a technical plan back to Redmine.

## Capture Checklist

Save screenshots and video in `docs/assets/`.

1. `01-redmine-issue-before.png`
   Show `http://localhost:3000/issues/1` before running the agent. The issue should contain the feature request and no AI technical plan comment yet.

2. `02-cli-run.png`
   Show the terminal command:

   ```powershell
   chcp 65001
   $env:PYTHONIOENCODING="utf-8"
   python -m app.main analyze --issue-id 1
   ```

The terminal should show CLI progress/log lines for Redmine access, repository scanning, LLM analysis, and successful completion. Do not show `.env` or API keys.

3. `03-redmine-ai-comment.png`
   Refresh the Redmine issue and show the generated `AI technical plan` comment with likely files, implementation steps, verification steps, risks, and analysis limits.

4. `04-redmine-subtasks.png`
   Show the issue metadata after analysis: status `In Progress`, priority `High`, progress `50%`, and generated child issues under the parent task.

5. `demo.mp4`
   Record a 60-90 second walkthrough:

   - Start on the Redmine issue.
   - Show that the task has no generated plan.
   - Run the CLI command.
   - Return to Redmine and refresh.
   - Show the generated technical plan.
   - Show the generated child issues and updated issue status.

## Demo Script

Use this narration:

> This is Redmine AI Technical Planner. It connects Redmine tasks with the matching Git repository. Here I have a Redmine issue asking for a category filter in BudgetBot. I run the CLI agent with the issue id. The agent reads the issue, resolves the Redmine project to the BudgetBot repository, scans only relevant files, sends limited context to the LLM, and posts a technical plan back into the same Redmine issue. It also moves the task to In Progress, sets progress to 50%, raises priority to High, and creates child issues from the generated subtasks. The result gives a developer likely files to inspect, what to change, verification steps, risks, effort estimate, and clear analysis limits. The agent does not modify code or create branches; it accelerates the first technical pass.

## What This Proves

- Redmine REST API integration works.
- Project-to-repository mapping works.
- The agent avoids sending the whole repository to the LLM.
- The output names likely files and explains why they matter.
- The generated plan is posted back into the existing developer workflow.
- Generated subtasks can become Redmine child issues for follow-up implementation work.

## Safety Notes

- Do not record `.env`.
- Do not show OpenRouter or Redmine API keys.
- Do not use real client issues or private code in portfolio material.
- Keep the live Redmine demo local unless authentication, rate limits, and cost controls are added.

## Resetting the Demo

If you need a fresh issue, rerun:

```powershell
docker cp scripts/bootstrap_redmine_demo.rb redmine-ai-planner-app:/tmp/bootstrap_redmine_demo.rb
docker exec redmine-ai-planner-app bash -lc "bundle exec rails runner /tmp/bootstrap_redmine_demo.rb"
```

The bootstrap is idempotent: it reuses project `budgetbot` and the sample issue subject.

# Agents

This file contains project-level instructions for AI agents.

## Global Rules

- **Follow Clean Architecture**: Always prefer a clean architecture approach.
- **Documentation Conventions**: Never create or edit `CLAUDE.md` during normal work. Always use `AGENTS.md` for agent instructions.
- **Skills**: Refer to the [Skills README](./skills/README.md) for specialized agent capabilities.

## Refactor And Ralph Rules

- Read `docs/REFACTOR_PLAN.md` before planning, editing, or claiming completion for refactor work.
- Advance one open plan item at a time and keep changes scoped to that item.
- Update `docs/REFACTOR_PLAN.md` only when concrete evidence supports a status, evidence, or resume-note change.
- Record evidence as exact commands, file paths, runtime artifact paths, or observed error output.
- Use repo-owned scripts and prompts before ad hoc command chains when an entrypoint exists.
- For Ralph work, prefer `scripts/dev/ralph_checklist.sh`, `scripts/automation/ralph_checklist_watchdog.sh`, and `prompts/ralph-checklist-resolver.md`.
- For unattended Ralph work, prefer `scripts/dev/ralph_autoloop.sh`; `TODO` checklists are handoff data for the supervisor, not a request for the user to choose the next step.
- Worktree hygiene is a hard requirement for Ralph work. Start by recording `git status --short --untracked-files=all`; do not begin a new plan item on top of unrelated dirty state.
- Ralph workers must not leave uncommitted changes. Before final handoff, run verification, commit all intended changes with a descriptive message, and confirm `git status --short --untracked-files=all` is clean.
- If Ralph cannot verify and commit its changes, it must restore only its own edits or stop as blocked with exact evidence; it must not hide changes in stash or leave untracked files behind.
- Every worker handoff or final response must include `Done` and `TODO` checklists.

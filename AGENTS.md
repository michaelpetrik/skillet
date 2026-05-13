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
- Every worker handoff or final response must include `Done` and `TODO` checklists.

# Ralph Autonomy Setup

This repository has a Ralph-style autonomous development loop around `docs/REFACTOR_PLAN.md`.

## Commands

Prepare one run without launching a worker:

```bash
scripts/dev/ralph_checklist.sh --task "Advance the first unchecked Skillet refactor item without reverting user edits."
```

Launch a worker:

```bash
scripts/dev/ralph_checklist.sh --task "Advance the first unchecked Skillet refactor item without reverting user edits." --execute
```

Launch the higher-level loop that keeps spawning checklist workers until blocked, complete, or max iterations are reached:

```bash
scripts/dev/ralph_autoloop.sh \
  --task "Keep advancing Skillet refactor items without asking the user for next steps." \
  --execute
```

Use an optional quality command:

```bash
scripts/dev/ralph_checklist.sh \
  --task "Advance the first unchecked Skillet refactor item without reverting user edits." \
  --quality-command "make test"
```

Artifacts are written under `var/dev/ralph-checklist/runs/<run-id>/`.

## Rules

- Read repo instructions and `docs/REFACTOR_PLAN.md` before changing code.
- Advance one item per run.
- Update the plan only when evidence justifies a status change.
- Use `scripts/dev/ralph_autoloop.sh` for unattended continuation. `Done` and `TODO` remain required as audit handoff, but the autoloop consumes them and continues without asking the user for the next step.
- Treat worktree hygiene as mandatory. A Ralph run must start by recording `git status --short --untracked-files=all`.
- Do not start new work on top of unrelated dirty state. Resolve, verify, and commit existing plan-related changes first, or stop as blocked.
- A completed Ralph run must leave no uncommitted changes. Run verification, commit the intended diff, and confirm a clean `git status --short --untracked-files=all` before handoff.
- Do not use `git stash` to hide unfinished work, and do not use destructive cleanup commands. Restore only your own edits if a verified commit cannot be produced.
- Do not claim a live product orchestrator exists unless this repo has one.

Cron/watchdog operations are documented in `docs/ralph-checklist-watchdog.md`.

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
- Do not claim a live product orchestrator exists unless this repo has one.

Cron/watchdog operations are documented in `docs/ralph-checklist-watchdog.md`.

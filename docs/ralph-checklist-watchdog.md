# Ralph Checklist Watchdog

This repo owns a cron-driven watchdog that keeps work moving on `docs/REFACTOR_PLAN.md`.

## Runtime

- Entrypoint: `scripts/automation/ralph_checklist_watchdog.sh`
- Worker supervisor: `scripts/dev/ralph_autoloop.sh`
- Single-iteration worker wrapper: `scripts/dev/ralph_checklist.sh`
- Installer: `scripts/automation/install_ralph_checklist_watchdog_cron.sh`
- Runtime root: `var/automation/skillet-ralph-refactor-watchdog/`
- Cron log: `var/automation/skillet-ralph-refactor-watchdog/cron.log`
- Entrypoint log: `var/automation/skillet-ralph-refactor-watchdog/watchdog.log`
- Events: `var/automation/skillet-ralph-refactor-watchdog/events.jsonl`
- Health: `var/automation/skillet-ralph-refactor-watchdog/health.json`
- Incidents: `var/automation/skillet-ralph-refactor-watchdog/incidents/`
- Cadence: every 40 minutes, expressed as minute `0,40` on even hours and minute `20` on odd hours.

## Behavior

Each run uses an explicit `PATH`, takes a non-blocking `flock`, scans `/proc` for `codex` or `claude` processes whose cwd or command line points at this repository, and records health.

If no repo agent is active, it checks the Git worktree before spawning. A dirty worktree blocks unattended recovery, writes `worktree-status.txt`, and records an incident instead of starting a new worker on top of uncommitted changes.

When the worktree is clean, it writes an incident artifact and starts `scripts/dev/ralph_autoloop.sh --execute`. The autoloop runs repeated checklist workers, verifies each clean commit, pushes to the upstream branch when configured, and continues until the plan is complete, a blocker is recorded, or `RALPH_AUTOLOOP_MAX_ITERATIONS` is reached. `TODO` handoff checklists are consumed as supervisor context and are not a user prompt.

For watchdog-owned runs, it checks whether run artifacts grow during the probe interval. If output stalls, it may start recovery after the cooldown.

Autoloop controls live in `var/automation/skillet-ralph-refactor-watchdog/watchdog.env`:

- `RALPH_AUTOLOOP_MAX_ITERATIONS`: maximum checklist workers per supervisor run. Default: `6`.
- `RALPH_AUTOLOOP_PUSH`: push committed clean work to the upstream branch. Default: `true`.
- `RALPH_AUTOLOOP_QUALITY_COMMAND`: command run around worker iterations. Default: `scripts/ci/run_quality_gates.sh`.

## Operator Commands

Install or refresh cron:

```bash
scripts/automation/install_ralph_checklist_watchdog_cron.sh
```

Inspect cron:

```bash
crontab -l | grep 'ralph-checklist-watchdog'
```

Disable without editing crontab:

```bash
sed -i 's/^RALPH_WATCHDOG_ENABLED=.*/RALPH_WATCHDOG_ENABLED=false/' \
  var/automation/skillet-ralph-refactor-watchdog/watchdog.env
```

Run one manual check:

```bash
RALPH_WATCHDOG_ENABLED=true scripts/automation/ralph_checklist_watchdog.sh
```

Run one manual autoloop:

```bash
scripts/dev/ralph_autoloop.sh --execute --max-iterations 3
```

Review status:

```bash
cat var/automation/skillet-ralph-refactor-watchdog/health.json
tail -n 50 var/automation/skillet-ralph-refactor-watchdog/events.jsonl
tail -n 50 var/automation/skillet-ralph-refactor-watchdog/watchdog.log
```

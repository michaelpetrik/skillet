# Ralph Checklist Watchdog

This repo owns a cron-driven watchdog that keeps work moving on `docs/REFACTOR_PLAN.md`.

## Runtime

- Entrypoint: `scripts/automation/ralph_checklist_watchdog.sh`
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

If no repo agent is active, it writes an incident artifact and starts `scripts/dev/ralph_checklist.sh --execute`. For watchdog-owned runs, it checks whether run artifacts grow during the probe interval. If output stalls, it may start recovery after the cooldown.

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

Review status:

```bash
cat var/automation/skillet-ralph-refactor-watchdog/health.json
tail -n 50 var/automation/skillet-ralph-refactor-watchdog/events.jsonl
tail -n 50 var/automation/skillet-ralph-refactor-watchdog/watchdog.log
```

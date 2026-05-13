# Skillet CLI

Skillet is a lightweight CLI for administering the skills published from this repository.

```bash
npx skillet --help
bunx skillet --help
```

> npm already has an unscoped `skillet` package. This manifest uses the requested package name and binary name, so publishing under `skillet` requires ownership or transfer of that npm package. If the package must be published under a scope, change `name` to something like `@michaelpetrik/skillet`; the installed binary can still remain `skillet`.

## Commands

```bash
skillet list
skillet check
skillet install repo-quality-guardrails
skillet install repo-quality-guardrails --global
skillet upgrade
skillet upload ./my-skill coding --dry-run
```

`install` and `upgrade` call `skills add michaelpetrik/skillet --skill <name>` through `npx` by default. Use `--runner bunx` to run through Bun.

Project scoped installs pass `-y`. Global installs pass `-g -y`.

## Development

```bash
npm install
npm run build
node dist/cli.js list
npm pack --dry-run
```

## Ralph loop

- Prepare a supervised refactor run: `scripts/dev/ralph_checklist.sh --task "Advance the next refactor item"`
- Execute the prepared run with Codex: `scripts/dev/ralph_checklist.sh --execute --task-id T-YYYY-MM-DD-name --task "Advance the next refactor item"`
- Run the watchdog once: `scripts/automation/ralph_checklist_watchdog.sh`
- Install/update the cron watchdog: `scripts/automation/install_ralph_checklist_watchdog_cron.sh`
- Resolver prompt: `prompts/ralph-checklist-resolver.md`

The loop uses `docs/REFACTOR_PLAN.md` as its checklist and writes runtime artifacts under `var/`.

## Publishing

```bash
npm publish --dry-run
bun publish --dry-run
```

Remove `--dry-run` when the package name and registry access are ready.

`bun publish` uses the npm registry. If Bun reports missing authentication, run `bunx npm login` first.

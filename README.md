# Skillet CLI

Skillet is a lightweight CLI for administering the skills published from this repository.

The package manifest is scoped as `@michaelpetrik/skillet`; the installed binary remains `skillet`.

After the package is made publishable and released:

```bash
npx @michaelpetrik/skillet --help
bunx @michaelpetrik/skillet --help
```

> npm already has an unscoped `skillet` package. This manifest keeps the binary name as `skillet` but avoids the taken package name. It is currently `private: true` and `UNLICENSED`, so public publishing remains blocked until npm scope access and license intent are deliberately reviewed.

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
npm run quality
scripts/dev/install_git_hooks.sh
scripts/ci/run_quality_gates.sh
npm run security:review
node dist/cli.js list
npm pack --dry-run
```

`scripts/dev/install_git_hooks.sh` sets `core.hooksPath` to `.githooks`. The
pre-commit hook runs the changed-file secret scan before `npm test`; the
pre-push hook runs the full quality gate, including the pack dry-run and
configured Sentrux checks.

`npm run security:review` performs an all-files secret scan and reports npm
advisory coverage as partial unless run with `-- --with-advisory`, which uses
live registry data.

## Ralph loop

- Prepare a supervised refactor run: `scripts/dev/ralph_checklist.sh --task "Advance the next refactor item"`
- Execute the prepared run with Codex: `scripts/dev/ralph_checklist.sh --execute --task-id T-YYYY-MM-DD-name --task "Advance the next refactor item"`
- Run the watchdog once: `scripts/automation/ralph_checklist_watchdog.sh`
- Install/update the cron watchdog: `scripts/automation/install_ralph_checklist_watchdog_cron.sh`
- Resolver prompt: `prompts/ralph-checklist-resolver.md`

The loop uses `docs/REFACTOR_PLAN.md` as its checklist and writes runtime artifacts under `var/`.

## Publishing

The manifest currently sets `private: true`, so direct publishing is intentionally blocked. Before a public release, confirm access to the `@michaelpetrik` npm scope, choose and record the license intent, remove `private`, and add the intended `publishConfig.access`.

```bash
npm publish --dry-run
bun publish --dry-run
```

Remove `--dry-run` when the package name and registry access are ready.

`bun publish` uses the npm registry. If Bun reports missing authentication, run `bunx npm login` first.

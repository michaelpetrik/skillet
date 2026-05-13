# Skillet Refactor Plan

Last reviewed: 2026-05-14

## Goal

Refactor the Skillet TypeScript CLI toward clean architecture, SOLID, DRY, KISS, and YAGNI while preserving the current command behavior and packaging intent.

## Operating Rules

- Read `AGENTS.md` before changing code.
- Treat tracked and untracked files as user work. Do not run `git reset`, `git checkout`, `git clean`, or revert unrelated edits.
- Advance one open item at a time.
- Prefer characterization tests before moving behavior.
- Do not start broad module extraction or rewrites before R3 is complete; before then, limit work to tests, docs, guardrail metadata, release identity, and narrow safety fixes.
- Keep changes small enough to verify with local commands.
- Treat this file as Ralph's source of truth. Update status or evidence only when local evidence supports the status change.
- Every worker handoff must include `Done` and `TODO` checklists.

## Status Legend

- `[ ]` open
- `[~]` in progress
- `[x]` complete
- `[!]` blocked

## Quality Gate

Use this command while the refactor is in progress:

```bash
npm run typecheck && npm run build && node dist/cli.js --help >/dev/null && node dist/cli.js list --json >/tmp/skillet-list.json && node dist/cli.js check && npm pack --dry-run >/tmp/skillet-npm-pack.txt && if [ -f .sentrux/rules.toml ]; then sentrux check .; else echo 'sentrux check skipped: .sentrux/rules.toml missing'; fi
```

After a real test script, secret scan, and Sentrux baseline exist, replace the transitional gate with a repo-owned script that includes `npm test`, `sentrux check .`, and `sentrux gate .`.

A backlog item is not complete unless its evidence column is satisfied by a local command, file diff, or explicit blocker note. Docs-only updates may verify with review and diff instead of the full gate.

## Current Baseline

- `npm run typecheck` passes.
- `npm run build` passes.
- `sentrux check .` passes against bootstrap `.sentrux/rules.toml` with permissive constraints; rules are observational, not final architecture enforcement.
- `sentrux gate .` has no saved baseline yet.
- No `npm test` script exists.
- No repo-owned quality script, hook installer, diff-aware secret scan, static security lint, or local security review entrypoint exists.
- No `packageManager`, `.nvmrc`, `.node-version`, Volta, or mise runtime pin exists beyond `engines.node >=20`.
- `src/cli.ts` currently owns parsing and output; command dispatch, help selection, option validation, list/check/install/upgrade planning, and skills-add process execution now use dedicated helpers.
- `src/upload.ts` currently owns planning, rendering, filesystem writes, clock access, and temp cleanup; Git operations now run through an injectable command runner seam.
- The unscoped npm name `skillet` is already taken by an unrelated package.
- `CLAUDE.md` exists as a regular file even though `AGENTS.md` is canonical.
- Repo-owned Ralph scripts and resolver prompt exist, `bash -n` passes for them, a supervised Ralph preflight with `scripts/ci/run_quality_gates.sh` passed, a supervised `--execute` worker run passed, the cron watchdog is installed, and Ralph now treats a clean committed worktree as a hard handoff requirement.

## Target Shape

Minimum viable direction:

- Keep `src/cli.ts` as a thin executable wrapper or composition root.
- Move behavior that can be pure into small domain/application functions.
- Keep filesystem, Git, process execution, clock, and environment access behind explicit seams.
- Split upload into a pure plan and a side-effect executor.
- Validate user-controlled paths and process arguments at application boundaries before any side effect.
- Preserve argument-vector process execution; do not convert external commands to shell-interpolated strings.
- Introduce Sentrux rules in staged mode only after tests and directory/module boundaries exist, then promote to a reviewed baseline.
- Resolve release identity before any packaging smoke or publish path claims readiness.
- Avoid a DI container, class-heavy framework, or broad rewrite.

## Refactor Backlog

| ID | Status | Area | Task | Evidence | Resume Notes |
| --- | --- | --- | --- | --- | --- |
| R0 | [x] | Baseline | Decide whether the new CLI package files are accepted as the baseline and keep them tracked together. | 2026-05-13: `git status --short --untracked-files=all` reviewed; accepted the current CLI package/refactor bootstrap file set as the baseline to keep together. | Do not normalize unrelated files; keep the manifest, lockfile, source, docs, scripts, prompts, README, `.gitignore`, and `.sentrux` files grouped in the eventual tracking change. |
| R1 | [x] | Agent docs | Normalize `CLAUDE.md` to an `AGENTS.md` compatibility stub or remove it if compatibility is not needed. | 2026-05-13: `CLAUDE.md` contains exactly `@AGENTS.md`; `AGENTS.md` remains the only real instruction source. | Do not create new prose in `CLAUDE.md`. |
| R2 | [x] | Skills index | Sync `skills/README.md` with all `skills/**/SKILL.md` entries. | 2026-05-13: `find skills -path '*/SKILL.md'` and README link extraction both report the same 9 skill directories. | Keep future skill additions reflected in `skills/README.md`. |
| R3 | [x] | Tests | Add a minimal test harness and pure characterization tests for version policy, frontmatter behavior, and upload target validation scaffolding. | 2026-05-13: `npm test` passed with 9 Node test-runner tests covering `domain` version policy and `frontmatter`, including CRLF delimiter parsing. | Add tests first for any future behavior move. |
| R4 | [x] | CLI safety | Reject unknown long CLI options before side effects. | 2026-05-13: `npm test` covers `list --dryrun` non-zero, flag value rejection, and `list --help` success; 12 tests passed. | Keep behavior explicit for aliases and help. |
| R5 | [x] | CLI design | Define and implement a small command metadata/option schema only if it removes real duplication. | 2026-05-13: `npm test` passed 15 tests covering alias help and metadata-backed option parsing; `scripts/ci/run_quality_gates.sh` passed secret scan, typecheck, build, tests, CLI smokes, npm pack dry-run, and `sentrux check .`, with `sentrux gate` skipped because `.sentrux/baseline.json` is missing. | Add future commands/options through the CLI metadata table so help, dispatch, and option validation stay aligned. |
| R6 | [x] | CLI use cases | Extract list/check/install/upgrade planning from presentation and process execution. | 2026-05-13: `src/cli-use-cases.ts` exports pure list/check/install/upgrade planners; `npm test` passed 19 tests including `test/cli-use-cases.test.mjs`; `scripts/ci/run_quality_gates.sh` passed secret scan, typecheck, build, tests, CLI smokes, npm pack dry-run, and `sentrux check .`, with `sentrux gate` skipped because `.sentrux/baseline.json` is missing. | Keep future CLI use-case decisions in application helpers; R7 should introduce the runner seam without reintroducing spawnable planning into `src/cli.ts`. |
| R7 | [x] | Process seams | Introduce a command runner seam for `npx`, `bunx`, and Git operations. | 2026-05-14: `src/command-runner.ts` exposes an injectable command runner, skills-add command builder, and Git runner; `test/command-runner.test.mjs` simulates `npx`/`bunx`/Git success and failure and asserts raw argument arrays; `npm test` passed 25 tests; `scripts/ci/run_quality_gates.sh` passed secret scan, typecheck, build, tests, CLI smokes, npm pack dry-run, and `sentrux check .`, with `sentrux gate` skipped because `.sentrux/baseline.json` is missing. | Keep future process execution behind `CommandRunner`; R8 should focus target path validation before mutations. |
| R8 | [ ] | Upload safety | Validate `targetName` and canonicalize target paths before any write, delete, Git add, or dry-run report. | Empty, dot, absolute, traversal, newline, and control-character fixtures fail before dry-run or live mutations; canonical targets remain under the skills root. | Apply equivalent fix to the legacy publisher script or remove it from the npm artifact; review write/delete/Git-add ordering. |
| R9 | [ ] | Upload planner | Split upload into pure planning plus side-effect application. | Dry-run and live mode derive from the same plan; `CHANGELOG.md` is not duplicated. | Inject date/clock. |
| R10 | [ ] | File discovery | Share skill file constants and discovery helpers without building a generic framework. | Duplicate `findSkillFiles` logic is reduced and traversal semantics remain explicit. | Preserve installed vs catalog traversal differences. |
| R11 | [~] | Sentrux | Tighten staged `.sentrux/rules.toml` after tests and module boundaries exist. | Bootstrap `.sentrux/rules.toml` exists and `sentrux check .` passes; final staged constraints remain pending. | Stage advisory rules first; document temporary allowances and promote only after R12 review. |
| R12 | [ ] | Sentrux baseline | Save a reviewed structural baseline. | `.sentrux/baseline.json` exists, was generated from reviewed R11 rules, and `sentrux gate .` passes without broad refresh. | Do not refresh baseline during normal worker runs. |
| R13 | [ ] | Release identity | Resolve `package.json` publish identity, bin name, repository metadata, publish config, and license intent. | `package.json` uses a scoped or otherwise owned npm name; license/private/publishConfig agree; README install examples and `npm pack --dry-run` output match. | Block release while the name is `skillet` unless npm ownership changes; do not publish public `UNLICENSED` unless intentional and documented. |
| R14 | [~] | Quality gates | Add a repo-owned quality script for typecheck, build, tests, pack dry-run, secret scan, and Sentrux when configured. | `scripts/ci/run_quality_gates.sh` exists and now runs secret scan, typecheck, build, `npm test`, CLI smokes, pack dry-run, and Sentrux check; final completion waits for reviewed `.sentrux/baseline.json` so `sentrux gate .` can run. | Keep pre-commit fast; secret scan must run before broader gates in hook/preflight paths; full pack gate belongs in push/CI/release. |
| R15 | [ ] | Secret scan | Add a repo-owned diff-aware secret scan and local security review entrypoint before broader quality gates. | Staged fake secret fixtures fail; `.env`, `.pem`, `.key`, and `.p12` files are blocked; current repo passes; output redacts values. | Do not print secret values; classify live registry/advisory checks as partial if they need network access. |
| R16 | [ ] | Packaging smoke | Verify package artifact from a clean build. | `npm pack --dry-run` shows intended files only, and a temp install smoke runs the packaged bin help/list paths after R13 is resolved. | Confirm no local junk ships. |
| R17 | [x] | Ralph loop | Verify the repo-owned Ralph checklist runner, watchdog, cron installer, and resolver prompt bound to this plan. | Ralph files exist; `bash -n` passes; non-execute preflight wrote `var/dev/ralph-checklist/runs/20260513T190455Z-T-2026-05-13-ralph-dev/status.json`; supervised `--execute` worker run wrote `var/dev/ralph-checklist/runs/20260513T200146Z-T-2026-05-13-ralph-dev/codex-final.md`; `scripts/automation/install_ralph_checklist_watchdog_cron.sh` installed two tagged crontab entries and a second run reported already up to date; 2026-05-14 worktree hygiene rules require Ralph to commit intended changes and leave clean status. | Cron can be disabled by setting `RALPH_WATCHDOG_ENABLED=false` in `var/automation/skillet-ralph-refactor-watchdog/watchdog.env`; dirty worktree blocks unattended spawn unless `RALPH_WATCHDOG_ALLOW_DIRTY_WORKTREE=true` is explicitly set; keep `.sentrux/baseline.json` and broader refactor work as separate reviewed items. |

## Evidence Log

- 2026-05-13: Three read-only review waves found missing Sentrux rules, missing tests, fat CLI/upload modules, release identity blockers, and no repo-owned Ralph loop.
- 2026-05-13: Worker 23 tightened this plan with explicit acceptance criteria for security controls, release identity, staged Sentrux rollout, Ralph handoff, and the no-broad-rewrite-before-tests rule.
- 2026-05-13: Worker 23 observed concurrent Sentrux and Ralph bootstrap files; `sentrux check .` and `bash -n` for Ralph scripts pass, while Sentrux baseline and Ralph preflight remain pending.
- 2026-05-13: Main thread ran `scripts/ci/run_quality_gates.sh` successfully, then ran `scripts/dev/ralph_checklist.sh --task "Verify Ralph refactor loop setup" --quality-command "scripts/ci/run_quality_gates.sh"` successfully without `--execute`; cron was installed later after the supervised worker run.
- 2026-05-13: R0 baseline decision recorded after `git status --short --untracked-files=all`; current CLI package/refactor bootstrap files are accepted as one grouped baseline for future tracking.
- 2026-05-13: Main thread ran supervised `scripts/dev/ralph_checklist.sh --task "Advance the first unchecked item in docs/REFACTOR_PLAN.md without reverting user edits." --quality-command "scripts/ci/run_quality_gates.sh" --execute`; it completed R0 and reported a passing repo-owned quality gate in `var/dev/ralph-checklist/runs/20260513T200146Z-T-2026-05-13-ralph-dev/codex-final.md`.
- 2026-05-13: Main thread installed cron with `scripts/automation/install_ralph_checklist_watchdog_cron.sh`; `crontab -l | grep 'skillet-ralph-refactor-watchdog'` shows even/odd tagged entries, and a second installer run reported `cron entries already up to date`.
- 2026-05-13: Main thread completed R1 by replacing `CLAUDE.md` with the exact compatibility stub `@AGENTS.md`.
- 2026-05-13: Main thread completed R2 by adding `enforce-offline-gates` and `google-ai-studio-export-standardizer` to `skills/README.md`.
- 2026-05-13: Main thread completed R3 by adding `npm test` with Node's built-in test runner plus `test/domain.test.mjs` and `test/frontmatter.test.mjs`; `npm test` passed 9 tests.
- 2026-05-13: Main thread completed R4 by rejecting unknown long CLI flags and flag values; `npm test` passed 12 tests including CLI option behavior.
- 2026-05-13: Watchdog worker completed R5 by replacing duplicate CLI command/help/option switches with a small metadata table in `src/cli.ts`; `npm test` passed 15 tests and `scripts/ci/run_quality_gates.sh` passed, with `sentrux gate` skipped because `.sentrux/baseline.json` is missing.
- 2026-05-13: Watchdog worker completed R6 by moving list/check/install/upgrade planning into `src/cli-use-cases.ts` and adding `test/cli-use-cases.test.mjs`; `npm test` passed 19 tests and `scripts/ci/run_quality_gates.sh` passed, with `sentrux gate` skipped because `.sentrux/baseline.json` is missing.
- 2026-05-14: Watchdog worker completed R7 by adding `src/command-runner.ts`, routing `skills add` and upload Git calls through the injectable runner seam, and adding `test/command-runner.test.mjs`; `npm test` passed 25 tests and `scripts/ci/run_quality_gates.sh` passed, with `sentrux gate` skipped because `.sentrux/baseline.json` is missing.
- 2026-05-14: Main thread tightened Ralph worktree hygiene in `AGENTS.md`, `prompts/ralph-checklist-resolver.md`, `scripts/dev/ralph_checklist.sh`, `scripts/automation/ralph_checklist_watchdog.sh`, and Ralph docs: workers must commit intended changes before handoff, wrapper records `git-status.before` and `git-status.after`, and unattended watchdog spawn is blocked on dirty worktree.

## Deferred Or Blocked

- Do not publish under unscoped `skillet` unless the npm package ownership is resolved.
- Do not treat Sentrux as architecture enforcement until rules match the actual codebase and a reviewed baseline exists.
- Do not treat secret scanning, security review, or local hooks as enforced until repo-owned scripts and activation paths exist.
- Do not begin R5-R10 broad extraction work until R3 is complete and `npm test` is in the gate.
- Do not add a full DI container or class-heavy architecture framework.
- Do not rely on unattended cron as release evidence; it is an implementation aid and must remain disableable via `var/automation/skillet-ralph-refactor-watchdog/watchdog.env`.

# Gates and Tools

## Minimum Gate Set

Prefer a single command that developers and agents can run:

```text
npm run quality
```

For JavaScript/TypeScript repos, this should usually compose:

```text
npm run typecheck
npm run lint
npm run test
npm run build
```

Adjust names for the repo ecosystem, but keep the same gate categories.

## Runtime Pinning

Use the repo's ecosystem conventions:

- Node: `engines`, `packageManager`, `.node-version` or `.nvmrc`
- Go: `go.mod` version and toolchain where appropriate
- Python: `.python-version` and lockfile, only if the repo already uses Python or there is a strong reason
- Docker: pinned base image versions, not floating `latest`

Record the runtime decision in an ADR if it changes project operation.

## Test Framework Selection

Pick the smallest framework that matches the repo:

- Vite/React: Vitest plus React Testing Library
- Node API: Vitest, Node test runner, or the repo's existing test framework
- Go: built-in `go test`
- Existing framework: extend it instead of adding a competing stack

The test command must support focused execution for red-green loops.

## Lint and Format

Prefer repo-standard tools. If none exist:

- TypeScript/React: ESLint with TypeScript and React hooks rules
- Formatting: Prettier only if the repo already expects broad formatting or the user asks for it

Avoid unrelated formatting churn while bootstrapping.

## Secret Scanning

Add a diff-aware secret scan before release or commit gates. Acceptable options depend on availability:

- `gitleaks protect --staged`
- `trufflehog git file://. --since-commit <base>`
- existing organization-approved scanner

If no scanner is available, document the blocker and add the gate as pending.

## GitNexus or Code Intelligence

If GitNexus is present:

1. Run or document `npx gitnexus analyze`.
2. Verify the index is non-empty for code repos.
3. Use impact analysis before symbol edits where repository rules require it.
4. Run detect-changes before commit/release gates.

If the index is empty, label GitNexus gates `policy-only` until analysis succeeds.

## TDD Split Gate

A task cannot enter implementation unless it has:

- `test_author.agent_id`
- failing test command
- expected failure description
- red evidence
- implementation author unset or different from test author
- owned implementation paths
- forbidden test paths for the implementation worker

A task cannot enter verification unless:

- `implementation_author.agent_id` exists
- `implementation_author.agent_id != test_author.agent_id`
- implementation worker did not edit test files
- green evidence exists for the same focused command

## Codex Spark Contract

Implementation workers using Codex Spark must receive:

- task ID
- goal
- owned paths
- forbidden paths
- AC and DoD
- failing test evidence
- commands to run
- maximum file count or diff scope
- explicit non-goals
- stop conditions

They must not receive broad architecture prompts.

## Release Gate

Before deployment promotion:

- quality command passes
- build artifact or image is created once
- version metadata is recorded
- route smoke passes
- health endpoint passes
- observability check passes where available
- rollback target is recorded
- human approval is recorded for production or privileged control-plane changes

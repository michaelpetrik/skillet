# Core Workflow

## 1. Extract local rules before proposing fixes

Read the repo in this order:

- `AGENTS.md`, `rules/`, `CONTRIBUTING*`, `docs/engineering*`, and task-specific policy files.
- `CLAUDE.md` if present, strictly to validate whether it is only a symlink to `AGENTS.md` or a file whose exact content is `@AGENTS.md`.
- GitNexus or equivalent code-intelligence artifacts: `.gitnexus/`, official `.claude/skills/gitnexus/*` skills, GitNexus-generated sections in `AGENTS.md`, bootstrap docs, freshness notes, and any required CLI or MCP workflow.
- Existing local entrypoints: `.githooks/`, `.husky/`, `.pre-commit-config.yaml`, `lefthook.yml`, `scripts/ci/`, `Makefile`, `justfile`, or equivalent.
- Toolchain and dependency manifests for the active stack.
- CI workflows and Dockerfiles to see what is enforced today.

Record each relevant control with:

- `control`
- `policy_source`
- `enforcement_source`
- `status`
- `reason`

Treat legacy, archived, or migration-only trees as out of scope unless the task explicitly targets them.

## 2. Separate policy from executable enforcement

Use these statuses consistently:

| Status | Meaning |
| --- | --- |
| `enforced` | The repo has a versioned, repo-owned executable path that developers can run locally, and CI uses the same path or a thin wrapper around it. |
| `partial` | Some executable logic exists, but it is not fully local, not pinned, not wired into hooks, or not equivalent to CI. |
| `policy-only` | The rule exists in prose, but there is no repo-owned executable check. |
| `blocker` | The repo says the control is required, but the needed manifest, tool, entrypoint, or evidence is missing. |
| `N/A` | The control does not apply to this repo or task. State why. |

Do not count CI-only behavior as `enforced` unless the same gate is available locally from a repo-owned entrypoint.

Do not count network-dependent scanners as local enforcement unless the repo also provides a pinned local mirror or cache strategy.

Do not count manual review alone as `enforced`. Manual review can be required output, but it remains human evidence, not executable enforcement.

## 3. Minimum control families

Every repo should either implement or explicitly classify these controls:

| Control | Minimum expectation | `N/A` only when |
| --- | --- | --- |
| GitNexus or equivalent code intelligence | Repo-owned graph or impact-analysis workflow for exploration, blast-radius checks, and change-scope verification. | The repo is not a meaningful source-code surface, or the task does not touch code. |
| Claude Code documentation naming | Use `$claudecode-conventions`; `AGENTS.md` is canonical and `CLAUDE.md` must be absent, a symlink to `AGENTS.md`, or a file whose exact content is `@AGENTS.md`. | The repo does not interact with Claude Code style agent docs at all. |
| Pinned toolchain manifest | Version-controlled source of truth for runtime, package manager, formatter, linter, test, and security tools. | Never. If missing, this is `blocker` or `policy-only`. |
| Local hook wiring | Repo-owned hook entrypoint plus reproducible installer or config. | Only when the repo intentionally has no pre-commit-style local gate. |
| Local quality gate | One local command or thin orchestrator that runs the pinned format, lint, test, build, and dependency-hygiene checks. | Never for active stacks. Missing means `blocker` or `partial`. |
| Local security review entrypoint | One local command or thin orchestrator that runs repo-owned static checks where applicable, secret scanning, and emits manual review obligations separately from executable results. | Never for active repos. Missing means `blocker` or `policy-only`. |
| Dependency vulnerability audit | A repo-owned advisory check with honest status. Local mirror or cache-backed paths can become `enforced`; live-network-only paths stay `partial` or `blocker`. | Only when the repo truly has no third-party dependencies. |
| Secret scanning | Diff-aware scan on changed content and secret-like files. | Never. Missing means `blocker` or `policy-only`. |
| Docker/runtime checks | Static hardening plus build and smoke verification for shipped containers or runtime packages. | No production container or runtime package exists. |
| Parseable handoff artifact | Machine-readable evidence for split test and implementation authorship when the repo requires it. | The repo does not require split authorship. |

Prefer small named scripts over one opaque monolith. A single top-level gate is fine if it delegates to smaller checks such as `check_agent_handoff`, `check_no_secrets`, or `check_docker_builds`.

For source-code repositories, GitNexus should be treated as a top-tier control alongside gates and manifests, not as optional documentation garnish. Prefer the official GitNexus skill set and generated context over hand-maintained local clones of the same workflow.

For repos that interact with Claude Code style agent docs, enforce `$claudecode-conventions` instead of inventing a local naming rule. `CLAUDE.md` should never survive as a normal hand-maintained instruction file.

## 4. Recommended handoff artifact

If the repo already has a required handoff path, keep that path and make the content parseable. If the repo has no existing home, propose a stable file such as `.quality/handoff.yaml`.

If the repo insists on Markdown, keep the Markdown file but put equivalent YAML front matter or a fenced YAML block at the top.

Recommended schema:

```yaml
schema_version: 1
task_id: "guardrails-task"
requires_split_authorship: true
scope:
  paths:
    - "src/example"
test_author:
  agent: "test-pass"
  completed_at: "2026-04-02T12:00:00Z"
  evidence:
    - "tests/example_test.*"
implementation_author:
  agent: "implementation-pass"
  started_after_handoff: true
  completed_at: null
verification:
  required_gates:
    - "quality"
    - "security"
  status: "pending"
na_controls: []
blockers: []
```

Required properties:

- stable keys, not free-form prose only;
- clear distinction between `test_author` and `implementation_author`;
- timestamps or equivalent ordering evidence;
- room for `na_controls` and `blockers`.

## 5. Explicit `N/A` reporting

Never silently omit a control. Use an explicit record such as:

```yaml
control: "docker_runtime"
status: "N/A"
reason: "No production Dockerfile or runtime entrypoint exists in this repo."
evidence: []
```

Good `N/A` examples:

- no production Dockerfile or release container exists;
- the repo does not require split authorship;
- the active language has no relevant concurrency safety mode.

Bad `N/A` examples:

- tool not installed locally;
- hook wiring not yet created;
- scanner needs network but the repo never mirrored its advisory data.

Those are `blocker` or `partial`, not `N/A`.

## 6. Delivery standard

When making or proposing changes:

- preserve repo-local naming and structure where possible;
- install and configure GitNexus when the repo lacks it and no equivalent exists, using the official `gitnexus-cli` bootstrap and official GitNexus skills for ongoing usage;
- keep GitNexus-specific AGENTS changes minimal; prefer the generated GitNexus context block plus links or references to the official GitNexus skills;
- use `$claudecode-conventions` to normalize `CLAUDE.md` handling: verify `AGENTS.md` exists, merge any actionable rules, then leave `CLAUDE.md` only as a symlink to `AGENTS.md` or a file whose exact content is `@AGENTS.md`;
- keep gates runnable offline after initial bootstrap;
- reuse the same entrypoints locally and in CI;
- split executable checks from network-dependent steps and manual obligations in the final matrix;
- state residual manual review boundaries for auth, input validation, injection sinks, secrets handling, templates, shell calls, and outbound requests.

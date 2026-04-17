---
name: repo-quality-guardrails
description: Use when you need to audit, add, or upgrade repository-local quality, documentation, and security guardrails without overreaching. Classify the task as audit, proposal, or implementation first; separate policy from executable enforcement; prefer the smallest repo-owned change set that closes real control gaps; and verify every claimed control with local evidence. Covers GitNexus or equivalent code intelligence, pinned manifests, activatable hook wiring, diff-aware secret scanning, offline documentation gates, Docker/runtime checks, handoff evidence, and Claude Code naming via `claudecode-conventions`.
category: Coding
version: 1.3.0
---

# Repo Quality Guardrails

Use this skill when a repo has quality or security policy in prose, but needs repo-owned guardrails that are reproducible, auditable, and honest about gaps.

## Operating Stance

1. Think before changing guardrails. First classify the task as `audit`, `proposal`, or `implementation`.
   - `audit`: inventory and classify controls; do not install new tooling just to make the matrix greener.
   - `proposal`: design the smallest credible change set and state tradeoffs.
   - `implementation`: change only the controls required by the task or already-proven repo policy.
2. Surface assumptions early. State the active stack, whether the repo is code-heavy enough for GitNexus or equivalent, whether Claude Code style docs apply, and whether docs, Docker, or handoff controls are actually relevant. If those assumptions change the recommendation, do not pick silently.
3. Simplicity first. Prefer the smallest repo-owned mechanism that satisfies the rule. Reuse existing hook managers, task runners, manifests, doc generators, and CI entrypoints before adding new wrappers, parallel frameworks, or redundant doc systems.
4. Make surgical changes. Every added file, script, or rule should trace to a discovered control gap. Do not rewrite adjacent policy, rename stable paths, or swap ecosystems unless the current path cannot satisfy the requirement.
5. Define success criteria before editing. For each control you change, name the exact local evidence that would prove it: command, hook path, manifest, generated artifact, or rendered output. For multi-step work, use a short plan of `step -> verify`.

## Workflow

1. Read repo-local instructions first: `AGENTS.md`, `rules/`, `CONTRIBUTING*`, existing hooks, `scripts/ci`, CI workflows, Dockerfiles, tool manifests, and any existing GitNexus or code-intelligence setup.
2. Build a policy-versus-enforcement inventory before proposing changes. Every control needs both its policy source and its executable evidence, or an explicit missing-status.
3. Separate what is required now from what is merely a backlog. Missing controls are not an automatic mandate to install everything at once.
4. Reuse repo-local filenames and entrypoints when they already exist. Only introduce new paths when the repo lacks a stable home for the control.
5. For active repos, require a versioned repo-owned local pre-commit entrypoint plus a reproducible activation path such as `.githooks/pre-commit` with an installer or explicit `core.hooksPath` config, or an equivalent checked-in mechanism. A bare `.pre-commit-config.yaml` without actual hook-path installation is not enough to call local hook wiring `enforced`.
6. Require a repo-owned diff-aware secret scan that runs before broader quality gates in the local hook path. It must inspect staged content, block secret-like file types such as `.env`, `.pem`, `.key`, `.p12`, and scan added lines for credential patterns. If this is missing, secret-scanning status is `blocker` or `policy-only`, never `enforced`.
7. Treat GitNexus or an equivalent repo-owned code-intelligence layer as a first-class control for non-trivial source repos. If it is absent and no equivalent exists, classify that gap honestly. Install and configure it only when the task scope is to close the gap, not during audit by reflex.
8. Enforce Claude Code documentation naming conventions with `$claudecode-conventions`: `AGENTS.md` is canonical, `CLAUDE.md` must not exist as a normal file, and any compatibility file must be only a symlink to `AGENTS.md` or a file whose exact content is `@AGENTS.md`.
9. Treat documentation as a first-class control for code-heavy repos, but choose the minimal credible offline-capable stack for the active language and repo scale. Do not bolt on a second generator, viewer, or graph system when a pinned repo-local stack already covers the need.
10. Prefer repo-owned manifests, installers, hook wiring, and local gates over ambient tools or `latest`.
11. When the active stack has a credible language-native documentation toolchain, require both the human-readable docs path and the renderer path to be either already wired or explicitly proposed. That usually means a local viewer or doc browser, a static generator, a structure or dependency visualizer, and offline renderers such as `plantuml` or Graphviz when the chosen tools emit source formats.
12. If the repo requires split test and implementation authorship, establish the handoff artifact before touching the guarded side of the change. Do not perform both roles in one pass.
13. Mark each control as `enforced`, `partial`, `policy-only`, `blocker`, or `N/A`. Never imply success where the repo cannot prove it.
14. If a control depends on network access, CI-only infrastructure, SaaS, or manual judgment, record that boundary explicitly and do not mark it `enforced`.
15. For implementation tasks, finish with exact verification evidence for each changed control. If verification is blocked, say what blocked it instead of silently claiming success.

## Read Next

- Read [references/workflow.md](references/workflow.md) for the core inventory, control families, handoff schema, and `N/A` rules.
- Read [references/gitnexus.md](references/gitnexus.md) when the repo is source-code heavy enough that code-intelligence, impact analysis, and refactor safety matter. Prefer the official GitNexus skills and generated context over custom AGENTS prose.
- Read [references/claudecode-conventions.md](references/claudecode-conventions.md) when the repo needs agent-doc naming cleanup or Claude Code compatibility handling.
- Read [references/generic.md](references/generic.md) when the repo is polyglot or the active stack is not Go, Python, or Node.js/TypeScript.
- Read [references/go.md](references/go.md) when the active stack is Go.
- Read [references/python.md](references/python.md) when the active stack is Python.
- Read [references/node-ts.md](references/node-ts.md) when the active stack is Node.js, JavaScript, or TypeScript.

## Outputs

Always produce:

- the task mode (`audit`, `proposal`, or `implementation`) and the key assumptions that changed the recommendation;
- the sourced list of discovered local rules and enforcement artifacts;
- a policy versus enforcement matrix with explicit `blocker` and `N/A` rows;
- the minimal change set required now versus optional backlog work, so audits do not turn into accidental platform rewrites;
- the GitNexus install or enforcement status, the `claudecode-conventions` status for `AGENTS.md` or `CLAUDE.md`, plus the pinned manifest, hook wiring, quality gate, documentation gate, secret-scan, Docker/runtime, and handoff changes you made or propose;
- whether local hook wiring is merely declared or actually activatable in a clone, including the exact installer/config path and whether secret scanning runs before broader quality gates;
- the established documentation stack selected for the active language, including which generator, viewer, visualizers, and renderers are pinned locally and whether README or docs indexes expose the generated artifacts offline;
- for every control you changed, the exact verification command, artifact, or postcondition that proves the change worked;
- any manual-review obligations and network or service dependencies that automation does not prove.

---
name: repo-quality-guardrails
description: Use when you need to add, audit, or upgrade repository-local quality, documentation, and security guardrails in a fresh or existing repo. This skill extracts local AGENTS and rules policy, separates policy from executable enforcement, and proposes or implements GitNexus-first code intelligence and impact analysis, pinned toolchain manifests, offline documentation gates, local hook wiring, local quality gates, security review entrypoints, diff-aware secret scanning, Docker and runtime checks, parseable handoff evidence with explicit N/A reporting, and Claude Code documentation naming conventions enforced via `claudecode-conventions`.
category: Coding
version: 1.1.0
---

# Repo Quality Guardrails

Use this skill when a repo has quality or security policy in prose, but needs repo-owned guardrails that are reproducible, auditable, and honest about gaps.

## Workflow

1. Read repo-local instructions first: `AGENTS.md`, `rules/`, `CONTRIBUTING*`, existing hooks, `scripts/ci`, CI workflows, Dockerfiles, tool manifests, and any existing GitNexus or code-intelligence setup.
2. Build a policy versus enforcement inventory before proposing changes. Every control needs both its policy source and its executable evidence, or an explicit missing-status.
3. Reuse repo-local filenames and entrypoints when they already exist. Only introduce new paths when the repo lacks a stable home for the control.
4. Treat GitNexus or an equivalent repo-owned code-intelligence layer as a first-class control. If GitNexus is absent in a non-trivial source repo and no equivalent exists, use the official GitNexus CLI and skill stack to install and configure it before calling the guardrail stack complete.
5. Enforce Claude Code documentation naming conventions with `$claudecode-conventions`: `AGENTS.md` is canonical, `CLAUDE.md` must not exist as a normal file, and any compatibility file must be only a symlink to `AGENTS.md` or a file whose exact content is `@AGENTS.md`.
6. Treat documentation as a first-class control for code-heavy repos. Select established, offline-capable documentation and architecture-visualization tooling for the active language, pin it in a repo-owned manifest, and wire it into the same local gates that developers and CI run.
7. Prefer repo-owned manifests, installers, hook wiring, and local gates over ambient tools or `latest`.
8. When the active stack has a credible language-native documentation toolchain, install both the human-readable docs path and the renderer path. That usually means a local viewer or doc browser, a static generator, a structure or dependency visualizer, and offline renderers such as `plantuml` or Graphviz when the chosen tools emit source formats.
9. If the repo requires split test and implementation authorship, establish the handoff artifact before touching the guarded side of the change. Do not perform both roles in one pass.
10. Mark each control as `enforced`, `partial`, `policy-only`, `blocker`, or `N/A`. Never imply success where the repo cannot prove it.
11. If a control depends on network access, CI-only infrastructure, SaaS, or manual judgment, record that boundary explicitly and do not mark it `enforced`.

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

- the sourced list of discovered local rules and enforcement artifacts;
- a policy versus enforcement matrix with explicit `blocker` and `N/A` rows;
- the GitNexus install or enforcement status, the `claudecode-conventions` status for `AGENTS.md` or `CLAUDE.md`, plus the pinned manifest, hook wiring, quality gate, documentation gate, secret-scan, Docker/runtime, and handoff changes you made or propose;
- the established documentation stack selected for the active language, including which generator, viewer, visualizers, and renderers are pinned locally and whether README or docs indexes expose the generated artifacts offline;
- any manual-review obligations and network or service dependencies that automation does not prove.

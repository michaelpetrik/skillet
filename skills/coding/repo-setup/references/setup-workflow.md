# Repo Setup Workflow

## Readiness Classes

- `new`: no meaningful project baseline or first commit.
- `existing-unprepared`: app exists, but gates, handoffs, and loop contracts are missing.
- `partially-prepared`: some gates exist, but TDD split, ADRs, or release controls are incomplete.
- `ready-for-looping`: quality gates, handoffs, split authorship, and release contracts are enforceable.

## Phase 0: Instruction and Baseline Audit

Read repo-local instructions before edits. Then inspect:

- git status, branch, remotes, and whether a baseline commit exists
- package manager and lockfile
- runtime pins: `.node-version`, `.nvmrc`, `engines`, `packageManager`, Docker base images
- scripts: typecheck, lint, test, build, quality/ci
- test framework and test locations
- lint/format config
- CI workflows and local hooks
- Dockerfile, Compose, deployment manifests, reverse proxy config
- ADR/docs locations
- GitNexus or equivalent code intelligence
- secret scanning and dependency audit
- current dirty/untracked files

Stop or scope down if the repo has uncommitted user work that makes baseline ownership unclear.

## Phase 1: Plan

Write a plan with:

- readiness class
- blockers
- ordered setup tasks
- files to create/change
- which tasks are documentation-only vs executable enforcement
- validation commands
- rollback strategy
- ADRs required

Do not proceed to implementation until the plan accounts for existing repo instructions.

## Phase 2: Architecture and Governance Records

Create or update:

- ADR for the three-loop AI development workflow
- `docs/ai-development/ralph-orchestration.md`
- `docs/ai-development/tdd-split-rules.md`
- `docs/ai-development/spark-prompt-contract.md`
- `docs/release/deployment-flow.md`

Keep docs enforceable: every policy should have a corresponding gate, artifact, or explicit `policy-only` label.

## Phase 3: Executable Guardrails

Add or normalize:

- runtime/package-manager pins
- `typecheck`, `lint`, `test`, `build`, `quality` or `ci`
- test framework
- lint/format framework
- diff-aware secret scan
- CI workflow or local equivalent
- GitNexus analyze/detect command if applicable

If the repo cannot support a gate yet, create a tracked blocker instead of pretending it passes.

## Phase 4: Ralph Contracts

Create `.ralph` contracts:

- bootstrap-quality loop
- tdd-spark-change loop
- release-deploy-observe loop
- task state schema
- handoff template
- Spark locked-task contract
- release checklist

If no Ralph runtime exists, mark these as `policy_mode: true`.

## Phase 5: Validation

Run all added commands. Also validate the process:

- Can a spec produce a locked task?
- Can a test handoff prove red before implementation?
- Can implementation be assigned to a different instance?
- Can a verifier reject same-author test/implementation?
- Can release handoff record version, build, smoke, rollback, and audit evidence?

Finish with a readiness state and concrete next blocker.

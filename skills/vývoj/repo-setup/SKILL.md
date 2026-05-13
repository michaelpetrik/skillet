---
name: repo-setup
description: Bootstrap or retrofit a repository for AI-orchestrated development with Ralph-style loops, quality gates, ADRs, TDD split authorship, Codex Spark implementation tasks, and release/deployment controls. Use when setting up a new repo, hardening an existing repo, adding the three-loop workflow for specification/TDD/deployment, creating repo-local `.ralph` contracts, defining DoD/AC/ADR templates, or preparing automated AI development guardrails.
category: Vývoj
version: 1.0.0
---

# Repo Setup

## Goal

Set up a repository so automated AI development can proceed safely through three gated loops:

1. **Specification loop**: analyze the repo, write specs, capture ADRs, define AC/DoD, and break work into locked tasks.
2. **TDD implementation loop**: enforce separate test and implementation authors, then let Codex Spark implement narrow red-to-green slices.
3. **Release/deployment loop**: package, version, deploy, observe, and rollback verified changes.

Do not start by coding features. First establish a reproducible repo baseline, quality gates, handoff artifacts, and governance.

## Workflow

1. **Read repo instructions first**
   - Read `AGENTS.md`, `CLAUDE.md`, `.cursor/rules`, `.github/copilot-instructions.md`, or equivalents.
   - Treat required split authorship, handoff, test, and commit rules as hard constraints.
   - If the repo already mandates separate test/implementation authors, preserve and strengthen that workflow.

2. **Analyze current readiness**
   - Inspect project type, package manager, runtime pins, test/lint/build scripts, CI, Docker/deploy files, hooks, secret scanning, GitNexus or equivalent code intelligence, and git baseline.
   - Classify the repo as `new`, `existing-unprepared`, `partially-prepared`, or `ready-for-looping`.
   - Read [references/setup-workflow.md](references/setup-workflow.md) for the readiness checklist and phase order.

3. **Write an implementation plan before edits**
   - Produce a phased plan with blockers, ordered tasks, expected files, validation commands, and rollback notes.
   - Separate documentation/policy changes from executable gates.
   - Do not create implementation tasks for Codex Spark until the test runner, handoff artifact, and split-authorship policy exist.

4. **Create or update architecture records**
   - Add an ADR for the AI development orchestration design.
   - Add ADRs for meaningful decisions about runtime pins, test framework, linting, CI, secret scan, Docker/deploy strategy, and agent execution permissions.
   - Use existing ADR location if present; otherwise use `docs/architecture/NNNN-*.md`.

5. **Install the repo-local scaffold**
   - Create human-readable docs under `docs/ai-development/` and `docs/release/`.
   - Create machine-readable contracts under `.ralph/`, but mark them as `policy-only` if the Ralph CLI/runtime is not installed.
   - Use [references/scaffold-contracts.md](references/scaffold-contracts.md) for the canonical file tree and templates.

6. **Implement guardrails point by point**
   - Runtime/package-manager pinning.
   - `typecheck`, `lint`, `test`, `build`, and a combined `quality` or `ci` command.
   - GitNexus or equivalent analyze/detect gates where available.
   - Diff-aware secret scanning.
   - CI or local hook wiring.
   - TDD split handoff artifact.
   - Spark locked-task contract.
   - Release checklist and rollback contract.
   - Use [references/gates-and-tools.md](references/gates-and-tools.md) for tool selection and gate expectations.

7. **Validate**
   - Run the exact commands added to the repo.
   - Confirm the `.ralph` contracts can represent a task from spec through release handoff.
   - Confirm test author and implementation author cannot be the same in the documented workflow.
   - Confirm Codex Spark tasks have no architecture decisions left open.
   - Summarize remaining blockers honestly.

## Required Invariants

- No implementation without a reviewed spec.
- No behavior change without a red test unless the task is explicitly classified as documentation-only or policy-only.
- No red-to-green task where `test_author == implementation_author`.
- No Codex Spark task without locked scope, allowed files, forbidden files, AC, DoD, failing test evidence, commands, and stop conditions.
- No deployment promotion without version, build evidence, smoke checks, rollback target, and audit trail.
- No Docker socket, `codex exec`, SSH, or deploy privilege in an implementation worker unless the task is explicitly a deployment/control-plane task and has separate approval.

## Ralph Status Handling

If `ralph` is unavailable:

- Still create `.ralph` as repo-local contracts.
- Mark loop configs as `policy_mode: true`.
- Do not claim enforcement exists.
- Add a bootstrap task to install or document the actual Ralph CLI/runtime and map the contracts to its schema.

If `ralph` is available:

- Inspect its version and config schema before writing `.ralph` files.
- Prefer adapting the scaffold to real Ralph config rather than inventing incompatible YAML.

## Output Shape

End with:

- files created/changed
- ADRs added/updated
- gates added and command results
- current repo readiness state
- remaining blockers before automated loops can run
- next locked task suitable for separate test authoring

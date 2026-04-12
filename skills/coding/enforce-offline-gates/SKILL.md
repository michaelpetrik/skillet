---
name: enforce-offline-gates
description: Enforce deterministic offline quality/security/performance/architecture gates in any repository by detecting current languages/frameworks/package managers, selecting compatible static-analysis tooling, installing and wiring tools, and enforcing execution via git hooks and CI entrypoints. Use when the user asks to set up or harden guardrails, create offline gates, enforce pre-commit/pre-push checks, standardize quality protocol across mixed stacks, or bootstrap repeatable gate workflows for Next.js, frontend, backend, monorepos, or polyglot projects.
category: Coding
version: 1.0.0
---

# Enforce Offline Gates

## Overview

Enforce a deterministic gate system that fails fast locally before CI. Detect project stack first, then install and wire only tooling that matches the detected or user-declared ecosystem.

## Workflow

### 1) Baseline and constraints
- Read repository instructions (`AGENTS.md`, existing `scripts/ci`, hook setup).
- Confirm user constraints:
- Strictness level (`block on warnings` vs `report warnings`).
- Scope (`all changed files` vs full repo).
- Mandatory categories (security, performance, architecture boundaries, dependency hygiene, tests, formatting).
- Do not proceed with tool installation until compatibility is known.

### 2) Detect stack and current state
- Run:
```bash
python3 scripts/detect_stack.py --repo .
```
- If user explicitly specifies language/framework/tooling, treat that as higher priority than autodetection.
- Use detection output to choose tools from `references/tooling-matrix.md`.

### 3) Build deterministic gate plan
- Run:
```bash
python3 scripts/build_gate_plan.py --repo . --format markdown
```
- Ensure plan always includes:
- deterministic commands (`--max-warnings 0`, `--deny-warnings`, non-interactive flags).
- one canonical entrypoint (`npm run quality`, `make quality`, etc.).
- offline execution (no SaaS dependency required to pass core gates).
- git hooks that invoke repo-owned scripts, not ad hoc command chains.

### 4) Implement in red-green-refactor sequence
- RED:
- Introduce/execute gate and capture initial failure for the intended reason.
- GREEN:
- Install tools, add configs, wire scripts/hooks, resolve compatibility failures.
- REFACTOR:
- Reduce duplication, normalize naming, keep one source of truth for gate execution.
- Update docs/protocol so developers cannot accidentally bypass the gate path.

### 5) Enforce execution path
- Add/update git hooks (`pre-commit`, `pre-push`) to call repo scripts.
- Ensure install/bootstrap script sets executable bits and configures `core.hooksPath`.
- Prevent bypass in process documentation:
- explicitly require gate commands before merge/release.
- explicitly forbid bypassing hooks/entrypoints without tracked exception.
- Keep policy in repository instruction file (`AGENTS.md` or user-specified equivalent).

### 6) Verify and evidence
- Run full required gates end-to-end.
- Report:
- installed tools and pinned versions.
- exact gate commands and hook paths.
- pass/fail results by category.
- unresolved exceptions with owner and expiry.

## Deterministic Requirements

- Use non-interactive commands only.
- Fail on warnings for static analyzers when feasible.
- Keep all gate logic in versioned repo scripts (`scripts/ci`, `tools`, `make`, etc.).
- Avoid hidden global dependencies; prefer project-local tool installation and lockfiles.
- Keep security review partly manual when required (spawn/process/network/database boundary review).

## Language and framework selection

- Read `references/tooling-matrix.md` to select base analyzers.
- Read `references/enforcement-contract.md` to normalize repository contracts.
- If no matrix profile matches exactly, compose:
- one formatter/linter pair.
- one type/static checker.
- one architecture/dependency boundary checker.
- one dependency/security scanner.
- one secrets scanner.
- one deterministic test command.

## Output contract

Return these artifacts in the target repository:
- Gate scripts (`quality`, `security`, `offline` or equivalent).
- Hook scripts (`pre-commit`, `pre-push`) and hook installer.
- Tool config files (lint/static/dependency/security).
- Updated policy/instruction document with mandatory workflow and non-bypass language.
- Verification summary containing executed commands and outcomes.

## Resources

- `scripts/detect_stack.py`: detect languages/frameworks/package-manager and existing guardrails.
- `scripts/build_gate_plan.py`: generate tooling and enforcement plan from detection.
- `references/tooling-matrix.md`: compatible tool matrix by ecosystem.
- `references/enforcement-contract.md`: repository-level contract for deterministic offline gates.

Use this skill to implement, not only advise: detect -> install -> wire -> enforce -> verify.

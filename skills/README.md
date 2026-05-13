# Skillet Skills

This directory contains specialized skills that extend the capabilities of AI agents working on this project.

## Design

- **[Design System Extractor](./design/design-system-extractor/SKILL.md)**: Extract a structured design system (tokens, atoms, molecules, organisms following atomic design) from Pencil .pen files, screenshots, web URLs, or HTML/CSS/Tailwind code. Produces reusable .pen skeleton, DESIGN.md, design-tokens.json, and AGENTS.md.

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill design-system-extractor
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill design-system-extractor
  ```

## General


- **[Claude Code Conventions](./general/claudecode-conventions/SKILL.md)**: Guidelines for Claude Code to maintain project structure and documentation naming (e.g., using `AGENTS.md` instead of `CLAUDE.md`).

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill claudecode-conventions
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill claudecode-conventions
  ```

- **[Repo Notes](./general/repo-notes/SKILL.md)**: Record metadata about the current project (purpose, tech stack, milestones, goals, skills, important info) into a personal index repository michaelpetrik/project-notes. Use this when the user just set up a new repo, wants to register the current project in their personal notes index, or asks to "zaznamenat projekt", "uložit info o projektu", "publish project notes".

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill repo-notes
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill repo-notes
  ```
## Tracing

- **[Codex Langfuse Hook](./tracing/codex-langfuse-hook/SKILL.md)**: Install or repair the global Codex Stop hook that exports session transcripts to Langfuse, then guide the user to set the required `LANGFUSE_*` globals in `~/.codex/.env`. Use when the user wants Codex sessions sent to Langfuse, wants the hook reinstalled, or wants project-local dotenv overrides for Langfuse routing.

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill codex-langfuse-hook
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill codex-langfuse-hook
  ```
## Misc

- **[Publish Skill To Skillet](./misc/publish-skill-to-skillet/SKILL.md)**: Publish or sync a local Codex skill bundle into the skillet repository under skills/<category>/<skill-name>, including SKILL.md, bundled resources, CHANGELOG.md, and skills/README.md updates.

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill publish-skill-to-skillet
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill publish-skill-to-skillet
  ```

## Research

- **[Multi-Analyst Synthesis](./research/multi-analyst-synthesis/SKILL.md)**: Parallel multi-pass analysis for comparative research, due diligence, literature scans, decision memo prep, structured brainstorming, multi-source synthesis, product or market research, risk assessment, investigative work, codebase analysis, and other knowledge-work where distinct analytic perspectives should work in parallel before one consolidator and one critical reviewer shape the final deliverable. Use when the task is ambiguous, high-stakes, evidence-rich, or benefits from competing frames; avoid for simple fact lookups, deterministic transforms, routine drafting, narrow tasks with one obvious authoritative path, or cases where direct tools answer the question better than orchestration.

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill multi-analyst-synthesis
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill multi-analyst-synthesis
  ```

## Coding

- **[Enforce Offline Gates](./coding/enforce-offline-gates/SKILL.md)**: Enforce deterministic offline quality/security/performance/architecture gates in any repository by detecting current languages/frameworks/package managers, selecting compatible static-analysis tooling, installing and wiring tools, and enforcing execution via git hooks and CI entrypoints. Use when the user asks to set up or harden guardrails, create offline gates, enforce pre-commit/pre-push checks, standardize quality protocol across mixed stacks, or bootstrap repeatable gate workflows for Next.js, frontend, backend, monorepos, or polyglot projects.

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill enforce-offline-gates
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill enforce-offline-gates
  ```

- **[Google AI Studio Export Standardizer](./coding/google-ai-studio-export-standardizer/SKILL.md)**: Standardize Google AI Studio exported React/Vite apps that use non-standard client env injection, mismatched aliases, or AI Studio-specific config hacks. Use when Codex needs to normalize an exported AI Studio app to idiomatic Vite patterns, keep the change reversible, update docs/examples, and add regression checks that protect both standardization and rollback.

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill google-ai-studio-export-standardizer
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill google-ai-studio-export-standardizer
  ```


- **[Repo Quality Guardrails](./coding/repo-quality-guardrails/SKILL.md)**: Use when you need to audit, add, or upgrade repository-local quality, documentation, and security guardrails without overreaching. Classify the task as audit, proposal, or implementation first; separate policy from executable enforcement; prefer the smallest repo-owned change set that closes real control gaps; and verify every claimed control with local evidence. Covers GitNexus or equivalent code intelligence, pinned manifests, activatable hook wiring, diff-aware secret scanning, offline documentation gates, Docker/runtime checks, handoff evidence, and Claude Code naming via `claudecode-conventions`.

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill repo-quality-guardrails
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill repo-quality-guardrails
  ```

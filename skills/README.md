# Skillet Skills

This directory contains specialized skills that extend the capabilities of AI agents working on this project.

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



- **[Repo Quality Guardrails](./coding/repo-quality-guardrails/SKILL.md)**: Use when you need to add, audit, or upgrade repository-local quality, documentation, and security guardrails in a fresh or existing repo. This skill extracts local AGENTS and rules policy, separates policy from executable enforcement, and proposes or implements GitNexus-first code intelligence and impact analysis, pinned toolchain manifests, offline documentation gates, local hook wiring, local quality gates, security review entrypoints, diff-aware secret scanning, Docker and runtime checks, parseable handoff evidence with explicit N/A reporting, and Claude Code documentation naming conventions enforced via `claudecode-conventions`.

  **Install using skills.sh:**

  With `npm`:
  ```bash
  npx skills add michaelpetrik/skillet --skill repo-quality-guardrails
  ```

  With `bun`:
  ```bash
  bunx skills add michaelpetrik/skillet --skill repo-quality-guardrails
  ```

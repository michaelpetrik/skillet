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

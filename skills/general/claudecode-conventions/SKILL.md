---
name: claudecode-conventions
description: Guidelines for Claude Code to maintain project structure and documentation naming.
category: General
version: 1.1.0
---

# Claude Code Conventions

This skill ensures that Claude Code (and other agents) follows specific project-level conventions for documentation.

## Guidelines

- **Never create `CLAUDE.md`**: This file is restricted or non-standard for this project's architecture.
- **Always use `AGENTS.md`**: All project-level agent instructions, context, or guidelines must be stored in `AGENTS.md`.
- **Handle Existing `CLAUDE.md`**: If a `CLAUDE.md` file already exists (e.g., copied from another project):
    1. **Extract Knowledge**: Move all useful knowledge, rules, and context from `CLAUDE.md` into `AGENTS.md`.
    2. **Reset `CLAUDE.md`**: Replace the contents of `CLAUDE.md` with the following exact content:
       ```markdown
       @AGENTS.md
       ```

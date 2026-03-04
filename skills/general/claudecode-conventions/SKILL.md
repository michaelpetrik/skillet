---
name: claudecode-conventions
description: Guidelines for Claude Code to maintain project structure and documentation naming.
category: General
version: 1.2.1
---

# Claude Code Conventions

This skill ensures that Claude Code (and other agents) follows specific project-level conventions for documentation.

## Guidelines

- **Never create `CLAUDE.md`**: This file is restricted or non-standard for this project's architecture.
- **Always use `AGENTS.md`**: All project-level agent instructions, context, or guidelines must be stored in `AGENTS.md`.
- **Handle Existing `CLAUDE.md`**: If a `CLAUDE.md` file already exists (e.g., copied from another project):
    1. **Validate preconditions**: Ensure `AGENTS.md` exists in repo root. If it is missing, stop and report an error.
    2. **Extract and merge rules**: Move actionable rules from `CLAUDE.md` into `AGENTS.md` without duplicating existing rules.
    3. **Detect symlink capability deterministically**: In the same directory as `CLAUDE.md`, try creating and then removing a temporary symlink.
    4. **If symlinks are supported**: Replace `CLAUDE.md` with a relative symlink whose target is exactly `AGENTS.md`. If symlink creation fails for any reason, use the fallback in step 5.
    5. **Fallback**: Replace the contents of `CLAUDE.md` with the following exact content:
       ```markdown
       @AGENTS.md
       ```
    6. **Verify postcondition**: Confirm that `CLAUDE.md` is either:
       - a symlink resolving to `AGENTS.md`, or
       - a regular file whose exact content is `@AGENTS.md`.

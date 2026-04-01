---
name: codex-langfuse-hook
description: Install or repair the global Codex Stop hook that exports session transcripts to Langfuse, then guide the user to set the required `LANGFUSE_*` globals in `~/.codex/.env`. Use when the user wants Codex sessions sent to Langfuse, wants the hook reinstalled, or wants project-local dotenv overrides for Langfuse routing.
category: Tracing
version: 1.0.0
---

# Codex Langfuse Hook

Use this skill when the task is to install, update, or repair the global Codex Langfuse transcript hook in `~/.codex`.

## Workflow

1. Run:

```bash
python3 /Users/michal/.codex/skills/codex-langfuse-hook/scripts/install_codex_langfuse_hook.py
```

2. Read the JSON output. It reports:
   - written files
   - whether `hooks.json` changed
   - which required globals are missing from `~/.codex/.env`

3. If `missing_global_vars` is non-empty, tell the user exactly to add those variable names to `~/.codex/.env`.
   Point them to `/Users/michal/.codex/langfuse.env.example`.

4. Never invent or echo secret values. If the user explicitly provides real values and asks you to write them, update `~/.codex/.env` directly.

5. Mention local override support when relevant:
   - current working directory `.codex/.env`
   - nearest ancestor `.codex.env`
   - then `.env.local`
   - then `.env`

6. If the user asks for verification, rerun the installer and confirm that:
   - `hooks_installed` includes `Stop` and `SessionStart`
   - `missing_global_vars` is empty

## What It Installs

- `~/.codex/hooks/langfuse_stop_export.sh`
- `~/.codex/hooks/langfuse_stop_export.py`
- `~/.codex/langfuse.env.example`
- hook registrations in `~/.codex/hooks.json` for `Stop` and `SessionStart`

## Notes

- The hook exports transcripts on `Stop`.
- `SessionStart` is used to replay previously spooled failed exports.
- Required globals and override precedence are documented in [references/configuration.md](./references/configuration.md).

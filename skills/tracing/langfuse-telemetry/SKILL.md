---
name: langfuse-telemetry
description: Set up and manage Claude Code session telemetry to self-hosted Langfuse with OTel metrics and Stop hook transcript exports.
category: Tracing
version: 1.1.1
allowed-tools: Read, Bash, Edit, Write, Glob
---

# Langfuse Telemetry

Credentials are read from `~/.agents/.env` at runtime (never stored in this skill).
Claude Code can use a separate Langfuse API keypair from Codex via
`CLAUDE_CODE_LANGFUSE_PUBLIC_KEY` and `CLAUDE_CODE_LANGFUSE_SECRET_KEY`.

## Commands

Route user intent to the appropriate script in this skill's `scripts/` directory:

| Intent | Script | Run as |
|--------|--------|--------|
| Initial setup / reconfigure | `lf-setup` | `bash scripts/lf-setup` |
| Diagnose problems | `lf-doctor` | `bash scripts/lf-doctor` |
| Check export queue status | `lf-status` | `bash scripts/lf-status` |
| Flush offline spool manually | `lf-drain` | `bash scripts/lf-drain` |

All scripts are in: `~/.claude/skills/langfuse-telemetry/scripts/`

## How It Works

```
Claude Code session
  ├─► OTel metrics (real-time) ──► Langfuse /api/public/otel
  └─► Stop hook (on exit) ──► langfuse_stop_export.py ──► Langfuse SDK
                                    │
                                    ├─ online: export immediately
                                    └─ offline: spool to ~/.claude/langfuse-export/spool/
                                                (auto-drain on next successful export)
```

## When things go wrong

Run `bash scripts/lf-doctor` — it checks everything: deps, credentials, connectivity,
settings.json hooks, spool health, and last export status.

## Files

- Hook: `~/Projects/langfuse-hooks/langfuse_stop_export.{sh,py}`
- Templates: `scripts/templates/langfuse_stop_export.{sh,py}`
- Credentials: `~/.agents/.env` (`CLAUDE_CODE_LANGFUSE_PUBLIC_KEY`, `CLAUDE_CODE_LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`)
- Spool: `~/.claude/langfuse-export/spool/`
- Log: `~/.claude/log/langfuse-export.log`

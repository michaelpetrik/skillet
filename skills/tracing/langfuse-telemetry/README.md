# langfuse-telemetry

Claude Code skill for exporting session telemetry to a self-hosted Langfuse instance.

## Architecture

```
Claude Code session
  │
  ├── OTel metrics (real-time)
  │   └── token counts, costs, session counts
  │   └── → Langfuse /api/public/otel (OTLP http/json)
  │
  └── Stop hook (on session end)
      └── langfuse_stop_export.py
          ├── online → Langfuse SDK ingestion API
          └── offline → ~/.claude/langfuse-export/spool/
                        (auto-drain on next successful export)
```

**Why two channels?** OTel handles aggregate metrics (dashboards, cost tracking).
The Stop hook exports complete raw JSONL transcripts (full conversation replay).
They don't overlap: OTel logs/traces exporters are set to `none`.

## File Layout

```
~/.claude/skills/langfuse-telemetry/   ← this skill (Claude Code reads SKILL.md)
├── SKILL.md                           ← dispatcher (~50 lines, no credentials)
├── VERSION                            ← semver
├── README.md                          ← you are here
└── scripts/
    ├── lf-setup                       ← interactive credential + config setup
    ├── lf-doctor                      ← comprehensive diagnostic check
    ├── lf-status                      ← quick spool/export status
    ├── lf-drain                       ← manual flush of offline queue
    └── templates/
        ├── langfuse_stop_export.sh    ← installed runtime wrapper
        └── langfuse_stop_export.py    ← installed runtime exporter

~/Projects/langfuse-hooks/             ← hook runtime (referenced by settings.json)
├── langfuse_stop_export.sh            ← shell wrapper (invoked by Claude Code)
└── langfuse_stop_export.py            ← Python export logic

~/.agents/.env                         ← shared config plus Claude-specific API keypair
~/.claude/settings.json                ← hook registration + OTel env vars
~/.claude/langfuse-export/             ← runtime state
├── spool/                             ← failed exports awaiting retry
├── exported/                          ← dedup markers (pruned to 500)
└── health/                            ← server health state (backoff tracking)
~/.claude/log/langfuse-export.log      ← activity log
```

## Setup

```bash
bash ~/.claude/skills/langfuse-telemetry/scripts/lf-setup
```

You'll be prompted for:
- `LANGFUSE_BASE_URL` — your Langfuse instance URL
- `CLAUDE_CODE_LANGFUSE_PUBLIC_KEY` — starts with `pk-lf-`
- `CLAUDE_CODE_LANGFUSE_SECRET_KEY` — starts with `sk-lf-`

The script saves credentials to `~/.agents/.env`, tests connectivity,
installs Python dependencies and installs the Stop hook with the `cc` profile.
The `cc` profile prevents Claude Code from falling back to Codex's generic
`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` pair.

## CLI Commands

| Command | What it does |
|---------|-------------|
| `lf-setup` | Interactive setup (credentials, deps, config) |
| `lf-doctor` | Full diagnostic: deps, credentials, connectivity, hooks, spool, log |
| `lf-status` | Quick view: queue depth, last export, health state |
| `lf-drain` | Flush spool queue (use `--force` to ignore backoff) |

Run from anywhere: `bash ~/.claude/skills/langfuse-telemetry/scripts/lf-doctor`

## Offline Resilience

When Langfuse is unreachable:

1. Export fails → session is written to spool (`~/.claude/langfuse-export/spool/`)
2. Health state records the failure with exponential backoff (15s → 30s → 60s → ... → 600s max)
3. Next session end triggers drain: spool entries are retried
4. On success: health state is cleared, backoff resets
5. Stale spool entries (>7 days) are automatically pruned
6. Manual drain: `lf-drain --force` clears backoff and retries immediately

## Security

- **No credentials in skill files** — everything reads from `~/.agents/.env` at runtime
- **Secret redaction** — basic mode masks keys, tokens, passwords in exported transcripts
- **Atomic spool writes** — write to `.tmp` then rename to prevent corruption
- **File locking** — `fcntl.flock` prevents concurrent export races

## Configuration

Environment variables (in `~/.agents/.env` or system env):

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_CODE_LANGFUSE_PUBLIC_KEY` | required | Claude Code Langfuse public key |
| `CLAUDE_CODE_LANGFUSE_SECRET_KEY` | required | Claude Code Langfuse secret key |
| `CLAUDE_CODE_LANGFUSE_BASE_URL` | `LANGFUSE_BASE_URL` | Optional Claude-specific Langfuse URL |
| `CLAUDE_CODE_LANGFUSE_ENABLED` | falls back | Claude Code-specific enable/disable flag |
| `CLAUDE_LANGFUSE_ENABLED` | `true` | Disable export entirely |
| `CLAUDE_LANGFUSE_REDACTION_MODE` | `basic` | `basic` = redact secrets, `none` = raw |
| `CLAUDE_LANGFUSE_TIMEOUT_SECONDS` | `6` | HTTP timeout per request |
| `CLAUDE_LANGFUSE_RAW_CHUNK_BYTES` | `180000` | Max bytes per transcript chunk |
| `CLAUDE_LANGFUSE_USER_ID` | `$USER` | User ID in Langfuse traces |
| `CLAUDE_LANGFUSE_TAGS` | `` | Extra comma-separated tags |

## Troubleshooting

```bash
# Full diagnostic
bash ~/.claude/skills/langfuse-telemetry/scripts/lf-doctor

# Check what's queued
bash ~/.claude/skills/langfuse-telemetry/scripts/lf-status

# Force-flush the queue
bash ~/.claude/skills/langfuse-telemetry/scripts/lf-drain --force

# Check recent log entries
tail -20 ~/.claude/log/langfuse-export.log

# Disable temporarily
echo 'CLAUDE_LANGFUSE_ENABLED=0' >> ~/.agents/.env
```

## Version History

See `VERSION` file. Current: 1.1.1

### 1.1.1

- Fix published skill metadata frontmatter formatting for Skillet

### 1.1.0

- Add `cc` Stop hook profile for Claude Code-specific Langfuse keys
- Keep project-local `.env` overrides higher priority than global `~/.agents/.env`
- Install bundled hook templates from the skill
- Prevent Claude Code from silently reusing Codex's generic Langfuse keypair

### 1.0.0

- Dual-channel telemetry (OTel metrics + Stop hook transcripts)
- Offline spool with exponential backoff
- CLI tools: lf-setup, lf-doctor, lf-status, lf-drain
- Secret redaction (basic mode)
- Atomic spool writes, file locking
- Automatic spool pruning (7-day max age)
- Exported marker pruning (500 max)

# Configuration

## Required Global Variables

These keys are the baseline global variables expected by the installer in `~/.codex/.env`:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_BASE_URL`

## Optional Variables

- `CODEX_LANGFUSE_ENABLED=true|false`
- `CODEX_LANGFUSE_PROJECT=<logical-label>`
- `CODEX_LANGFUSE_TAGS=tag1,tag2`
- `CODEX_LANGFUSE_USER_ID=<stable-user>`
- `CODEX_LANGFUSE_REDACTION_MODE=basic`
- `CODEX_LANGFUSE_RAW_CHUNK_BYTES=180000`
- `CODEX_LANGFUSE_TIMEOUT_SECONDS=4`

## Override Precedence

The installed hook layers configuration like this:

1. `~/.codex/.env`
2. current process environment overrides that
3. nearest ancestor override file overrides that, first match wins in this order:
   - `.codex.env`
   - `.env.local`
   - `.env`
4. current working directory `./.codex/.env` has the highest priority for any non-empty `LANGFUSE_*` / `CODEX_LANGFUSE_*` values; missing or blank values fall through to the earlier layers

## Local Project Override

Use a project-local `./.codex/.env` when the current repo should win over every other source for non-empty Langfuse values.
Use `.codex.env` when you want the existing nearest-ancestor override behavior instead.

Typical local override keys:

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_BASE_URL`
- `CODEX_LANGFUSE_PROJECT`
- `CODEX_LANGFUSE_TAGS`

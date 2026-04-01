#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script_path="$script_dir/langfuse_stop_export.py"
tmp_input="$(mktemp "${TMPDIR:-/tmp}/codex-langfuse-hook.XXXXXX")"
cwd="$(pwd -P 2>/dev/null || pwd)"
project_env_path="$cwd/.codex/.env"

cleanup() {
  rm -f "$tmp_input"
}

trap cleanup EXIT

if [[ -f "$project_env_path" ]]; then
  export CODEX_LANGFUSE_PROJECT_ENV_PATH="$project_env_path"
else
  unset CODEX_LANGFUSE_PROJECT_ENV_PATH || true
fi

if [[ $# -gt 0 && -n "${1:-}" ]]; then
  printf '%s' "$1" > "$tmp_input"
elif [[ ! -t 0 ]]; then
  cat > "$tmp_input" || true
else
  : > "$tmp_input"
fi

/usr/bin/env python3 "$script_path" --hook-input-file "$tmp_input" >/dev/null 2>&1 || true

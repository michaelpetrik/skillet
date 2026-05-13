#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script_path="$script_dir/langfuse_stop_export.py"
tmp_input="$(mktemp "${TMPDIR:-/tmp}/claude-langfuse-hook.XXXXXX")"
profile_args=()

cleanup() {
  rm -f "$tmp_input"
}

trap cleanup EXIT

if [[ $# -gt 0 && "${1:-}" == "cc" ]]; then
  profile_args=("cc")
  shift
fi

if [[ $# -gt 0 && -n "${1:-}" ]]; then
  printf '%s' "$1" > "$tmp_input"
elif [[ ! -t 0 ]]; then
  cat > "$tmp_input" || true
else
  : > "$tmp_input"
fi

/usr/bin/env python3 "$script_path" "${profile_args[@]}" --hook-input-file "$tmp_input" >/dev/null 2>&1 || true

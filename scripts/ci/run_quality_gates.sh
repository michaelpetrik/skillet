#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${SKILLET_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"

cd "$REPO_ROOT"

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/skillet-quality-gates.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT

run() {
  printf '\n==> %s\n' "$*"
  "$@"
}

run_capture() {
  local label="$1" output="$2"
  shift 2
  printf '\n==> %s\n' "$label"
  "$@" >"$output"
}

skip() {
  printf '\n==> skipped: %s\n' "$1"
}

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    printf 'required command not found: %s\n' "$name" >&2
    exit 127
  fi
}

run npm run security:review -- --offline

run npm run typecheck
run npm run build
run npm test

mkdir -p "$tmp_dir/global-skills"
run_capture "CLI help smoke" "$tmp_dir/skillet-help.txt" node dist/cli.js --help
run_capture "CLI list smoke" "$tmp_dir/skillet-list.json" \
  node dist/cli.js list --json --catalog "$REPO_ROOT" --project "$REPO_ROOT" --global-dir "$tmp_dir/global-skills"
run_capture "CLI check smoke" "$tmp_dir/skillet-check.txt" \
  node dist/cli.js check --catalog "$REPO_ROOT" --project "$REPO_ROOT" --global-dir "$tmp_dir/global-skills"

run npm run package:smoke

sentrux_rules="${SENTRUX_RULES_FILE:-.sentrux/rules.toml}"
sentrux_baseline="${SENTRUX_BASELINE_FILE:-.sentrux/baseline.json}"
sentrux_target="${SENTRUX_TARGET:-.}"

if [[ -f "$sentrux_rules" ]]; then
  require_command sentrux
  run sentrux check "$sentrux_target"

  if [[ -f "$sentrux_baseline" ]]; then
    run sentrux gate "$sentrux_target"
  else
    skip "sentrux gate ($sentrux_baseline missing)"
  fi
elif [[ -f "$sentrux_baseline" ]]; then
  require_command sentrux
  run sentrux gate "$sentrux_target"
else
  skip "sentrux check/gate ($sentrux_rules and $sentrux_baseline missing)"
fi

printf '\nquality gates passed\n'

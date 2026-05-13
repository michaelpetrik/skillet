#!/usr/bin/env bash
set -Eeuo pipefail

DEFAULT_PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
export PATH="${RALPH_WATCHDOG_PATH:-$DEFAULT_PATH}"
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
JOB_NAME="${RALPH_WATCHDOG_JOB_NAME:-skillet-ralph-refactor-watchdog}"
RUNTIME_ROOT="$REPO_ROOT/var/automation/$JOB_NAME"
ENV_FILE="$RUNTIME_ROOT/watchdog.env"
INSTALL_LOCK="$RUNTIME_ROOT/install.lock"
ENTRYPOINT="$REPO_ROOT/scripts/automation/ralph_checklist_watchdog.sh"
CRON_LOG="$RUNTIME_ROOT/cron.log"
TAG="# $JOB_NAME:ralph-checklist-watchdog"
PATH_VALUE="$DEFAULT_PATH"

umask 077
mkdir -p "$RUNTIME_ROOT"
exec 8>"$INSTALL_LOCK"
if ! flock -n 8; then
  printf '%s installer already running; skipping\n' "$JOB_NAME" >&2
  exit 0
fi
if ! command -v crontab >/dev/null 2>&1; then
  printf 'crontab command not found; cannot install %s\n' "$JOB_NAME" >&2
  exit 1
fi
if [[ ! -f "$ENTRYPOINT" ]]; then
  printf 'missing watchdog entrypoint: %s\n' "$ENTRYPOINT" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  tmp_env="$ENV_FILE.tmp.$$"
  {
    printf 'RALPH_WATCHDOG_ENABLED=true\n'
    printf 'RALPH_WATCHDOG_JOB_NAME=%s\n' "$JOB_NAME"
    printf 'RALPH_PLAN_FILE=docs/REFACTOR_PLAN.md\n'
    printf 'RALPH_WATCHDOG_MODEL=\n'
    printf 'RALPH_WATCHDOG_REASONING_EFFORT=xhigh\n'
    printf 'RALPH_WATCHDOG_PROBE_SECONDS=30\n'
    printf 'RALPH_WATCHDOG_STALL_RECOVERY_COOLDOWN_SECONDS=7200\n'
    printf 'RALPH_WATCHDOG_MIN_SPAWN_INTERVAL_SECONDS=60\n'
    printf 'RALPH_WATCHDOG_BYPASS_SANDBOX=true\n'
    printf 'RALPH_AUTOLOOP_MAX_ITERATIONS=6\n'
    printf 'RALPH_AUTOLOOP_PUSH=true\n'
    printf 'RALPH_AUTOLOOP_QUALITY_COMMAND=scripts/ci/run_quality_gates.sh\n'
  } >"$tmp_env"
  mv "$tmp_env" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
else
  chmod 600 "$ENV_FILE"
fi

ensure_env_key() {
  local key="$1" value="$2"
  if ! grep -q "^$key=" "$ENV_FILE"; then
    printf '%s=%s\n' "$key" "$value" >>"$ENV_FILE"
  fi
}

if [[ -s "$ENV_FILE" ]]; then
  last_env_byte="$(tail -c 1 "$ENV_FILE" | od -An -t x1 | tr -d '[:space:]')"
  if [[ "$last_env_byte" != "0a" ]]; then printf '\n' >>"$ENV_FILE"; fi
fi

ensure_env_key "RALPH_WATCHDOG_ENABLED" "true"
ensure_env_key "RALPH_WATCHDOG_JOB_NAME" "$JOB_NAME"
ensure_env_key "RALPH_PLAN_FILE" "docs/REFACTOR_PLAN.md"
ensure_env_key "RALPH_WATCHDOG_MODEL" ""
ensure_env_key "RALPH_WATCHDOG_REASONING_EFFORT" "xhigh"
ensure_env_key "RALPH_WATCHDOG_PROBE_SECONDS" "30"
ensure_env_key "RALPH_WATCHDOG_STALL_RECOVERY_COOLDOWN_SECONDS" "7200"
ensure_env_key "RALPH_WATCHDOG_MIN_SPAWN_INTERVAL_SECONDS" "60"
ensure_env_key "RALPH_WATCHDOG_BYPASS_SANDBOX" "true"
ensure_env_key "RALPH_AUTOLOOP_MAX_ITERATIONS" "6"
ensure_env_key "RALPH_AUTOLOOP_PUSH" "true"
ensure_env_key "RALPH_AUTOLOOP_QUALITY_COMMAND" "scripts/ci/run_quality_gates.sh"

chmod +x "$ENTRYPOINT"
: >>"$CRON_LOG"

cron_cmd=". \"$ENV_FILE\" && PATH=\"$PATH_VALUE\" /bin/bash \"$ENTRYPOINT\" >> \"$CRON_LOG\" 2>&1"
line_even="0,40 0-23/2 * * * $cron_cmd $TAG even"
line_odd="20 1-23/2 * * * $cron_cmd $TAG odd"

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/skillet-ralph-cron.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT

current="$tmp_dir/current"
stripped="$tmp_dir/stripped"
new="$tmp_dir/new"
backup="$RUNTIME_ROOT/crontab.$(date -u +%Y%m%dT%H%M%SZ).bak"

crontab -l >"$current" 2>/dev/null || true
cp "$current" "$backup"
grep -vF "$TAG" "$current" >"$stripped" || true
awk 'NF { while (blank_count > 0) { print ""; blank_count-- } print; next } { blank_count++ }' "$stripped" >"$stripped.trimmed"
mv "$stripped.trimmed" "$stripped"

{
  if [[ -s "$stripped" ]]; then
    cat "$stripped"
    printf '\n'
  fi
  printf '%s\n%s\n' "$line_even" "$line_odd"
} >"$new"

if cmp -s "$current" "$new"; then
  printf '%s cron entries already up to date\n' "$JOB_NAME"
else
  crontab -n "$new" >/dev/null
  crontab "$new"
  printf 'installed %s cron entries\n' "$JOB_NAME"
fi

printf '%s\n' "$line_even"
printf '%s\n' "$line_odd"
printf 'env file: %s\n' "$ENV_FILE"
printf 'runtime root: %s\n' "$RUNTIME_ROOT"
printf 'previous crontab backup: %s\n' "$backup"

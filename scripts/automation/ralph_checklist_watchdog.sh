#!/usr/bin/env bash
set -Eeuo pipefail

DEFAULT_PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"
export PATH="${RALPH_WATCHDOG_PATH:-$DEFAULT_PATH}"
export LC_ALL=C

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${RALPH_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"
JOB_NAME="${RALPH_WATCHDOG_JOB_NAME:-skillet-ralph-refactor-watchdog}"
PLAN_FILE="${RALPH_PLAN_FILE:-docs/REFACTOR_PLAN.md}"
RALPH_ENTRYPOINT="${RALPH_WATCHDOG_RALPH_ENTRYPOINT:-$REPO_ROOT/scripts/dev/ralph_checklist.sh}"
RUNTIME_ROOT="${RALPH_WATCHDOG_RUNTIME_ROOT:-$REPO_ROOT/var/automation/$JOB_NAME}"
LOCK_FILE="$RUNTIME_ROOT/watchdog.lock"
EVENTS_FILE="$RUNTIME_ROOT/events.jsonl"
HEALTH_FILE="$RUNTIME_ROOT/health.json"
WATCHDOG_LOG="$RUNTIME_ROOT/watchdog.log"
ACTIVE_AGENTS_FILE="$RUNTIME_ROOT/active-agents.tsv"
INCIDENT_DIR="$RUNTIME_ROOT/incidents"
RUNS_DIR="$RUNTIME_ROOT/runs"
PROBE_SECONDS="${RALPH_WATCHDOG_PROBE_SECONDS:-30}"
STALL_RECOVERY_COOLDOWN_SECONDS="${RALPH_WATCHDOG_STALL_RECOVERY_COOLDOWN_SECONDS:-7200}"
MIN_SPAWN_INTERVAL_SECONDS="${RALPH_WATCHDOG_MIN_SPAWN_INTERVAL_SECONDS:-60}"

umask 077
mkdir -p "$RUNTIME_ROOT" "$INCIDENT_DIR" "$RUNS_DIR"
exec >>"$WATCHDOG_LOG" 2>&1

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf '%s %s already running; skipping\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$JOB_NAME"
  exit 0
fi

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
normalize_uint() {
  local value="$1" fallback="$2"
  case "$value" in ''|*[!0-9]*) printf '%s' "$fallback" ;; *) printf '%s' "$value" ;; esac
}
json_escape() {
  local s="${1-}"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}
shell_quote() { printf '%q' "$1"; }

PROBE_SECONDS="$(normalize_uint "$PROBE_SECONDS" 30)"
STALL_RECOVERY_COOLDOWN_SECONDS="$(normalize_uint "$STALL_RECOVERY_COOLDOWN_SECONDS" 7200)"
MIN_SPAWN_INTERVAL_SECONDS="$(normalize_uint "$MIN_SPAWN_INTERVAL_SECONDS" 60)"

emit_event() {
  printf '{"ts":"%s","event":"%s","message":"%s"}\n' \
    "$(ts)" "$(json_escape "$1")" "$(json_escape "${2-}")" >>"$EVENTS_FILE"
}

write_health() {
  local status="$1" reason="$2" active_count="$3" latest_run="${4-}" tmp="$HEALTH_FILE.tmp"
  {
    printf '{\n'
    printf '  "ts": "%s",\n' "$(ts)"
    printf '  "job": "%s",\n' "$(json_escape "$JOB_NAME")"
    printf '  "status": "%s",\n' "$(json_escape "$status")"
    printf '  "reason": "%s",\n' "$(json_escape "$reason")"
    printf '  "active_agent_count": %s,\n' "$active_count"
    printf '  "latest_run": "%s",\n' "$(json_escape "$latest_run")"
    printf '  "plan_file": "%s",\n' "$(json_escape "$PLAN_FILE")"
    printf '  "events_file": "%s",\n' "$(json_escape "$EVENTS_FILE")"
    printf '  "watchdog_log": "%s"\n' "$(json_escape "$WATCHDOG_LOG")"
    printf '}\n'
  } >"$tmp"
  mv "$tmp" "$HEALTH_FILE"
}

write_incident() {
  local reason="$1" active_count="$2" latest_run="${3-}" safe_reason path agents_snapshot
  safe_reason="${reason//[^A-Za-z0-9_-]/-}"
  path="$INCIDENT_DIR/$(date -u +%Y%m%dT%H%M%SZ)-$safe_reason.json"
  agents_snapshot="$path.active-agents.tsv"
  if [[ -f "$ACTIVE_AGENTS_FILE" ]]; then cp "$ACTIVE_AGENTS_FILE" "$agents_snapshot"; else : >"$agents_snapshot"; fi
  {
    printf '{\n'
    printf '  "ts": "%s",\n' "$(ts)"
    printf '  "job": "%s",\n' "$(json_escape "$JOB_NAME")"
    printf '  "reason": "%s",\n' "$(json_escape "$reason")"
    printf '  "active_agent_count": %s,\n' "$active_count"
    printf '  "latest_run": "%s",\n' "$(json_escape "$latest_run")"
    printf '  "active_agents_snapshot": "%s",\n' "$(json_escape "$agents_snapshot")"
    printf '  "events_file": "%s",\n' "$(json_escape "$EVENTS_FILE")"
    printf '  "health_file": "%s",\n' "$(json_escape "$HEALTH_FILE")"
    printf '  "watchdog_log": "%s"\n' "$(json_escape "$WATCHDOG_LOG")"
    printf '}\n'
  } >"$path"
  emit_event "incident" "$reason -> $path"
}

find_active_agents() {
  local proc pid comm cmd cwd stat
  for proc in /proc/[0-9]*; do
    [[ -d "$proc" ]] || continue
    pid="${proc##*/}"
    [[ "$pid" == "$$" || "$pid" == "$BASHPID" ]] && continue
    comm="$(cat "$proc/comm" 2>/dev/null || true)"
    cmd="$(tr '\0' ' ' <"$proc/cmdline" 2>/dev/null || true)"
    case "$comm $cmd" in *codex*|*claude*) ;; *) continue ;; esac
    cwd="$(readlink -f "$proc/cwd" 2>/dev/null || true)"
    case "$cwd" in "$REPO_ROOT"|"$REPO_ROOT"/*) ;; *) case "$cmd" in *"$REPO_ROOT"*) ;; *) continue ;; esac ;; esac
    stat="$(awk '{print $3}' "$proc/stat" 2>/dev/null || printf '?')"
    cmd="${cmd//$'\t'/ }"
    cmd="${cmd//$'\n'/ }"
    printf '%s\t%s\t%s\t%s\t%s\n' "$pid" "$stat" "$comm" "$cwd" "$cmd"
  done
}

latest_run_dir() {
  if [[ -L "$RUNTIME_ROOT/current-run" ]]; then readlink -f "$RUNTIME_ROOT/current-run" 2>/dev/null || true; return; fi
  find "$RUNS_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR == 1 { sub(/^[^ ]+ /, ""); print }'
}

run_output_size() {
  local run_dir="$1"
  [[ -n "$run_dir" && -d "$run_dir" ]] || { printf '0'; return; }
  find "$run_dir" -type f \( -name '*.jsonl' -o -name '*.log' -o -name '*.stdout' -o -name '*.stderr' -o -name '*final.md' \) -printf '%s\n' 2>/dev/null \
    | awk '{ total += $1 } END { printf "%d", total }'
}

worktree_status() {
  if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$REPO_ROOT" status --short --untracked-files=all
  else
    printf 'not a git worktree\n'
  fi
}

last_spawn_epoch() {
  local stamp="$RUNTIME_ROOT/last-spawn.epoch"
  if [[ -f "$stamp" ]]; then cat "$stamp" 2>/dev/null || printf '0'; else printf '0'; fi
}
mark_spawn_epoch() { date -u +%s >"$RUNTIME_ROOT/last-spawn.epoch"; }

pid_is_watchdog_process() {
  local pid="$1" run_dir="$2" proc="/proc/$pid" cmd cwd
  [[ -d "$proc" ]] || return 1
  cmd="$(tr '\0' ' ' <"$proc/cmdline" 2>/dev/null || true)"
  cwd="$(readlink -f "$proc/cwd" 2>/dev/null || true)"
  case "$cmd" in *"$run_dir"*|*"$RALPH_ENTRYPOINT"*|*codex*|*claude*) ;; *) return 1 ;; esac
  case "$cwd" in "$REPO_ROOT"|"$REPO_ROOT"/*) return 0 ;; esac
  case "$cmd" in *"$REPO_ROOT"*) return 0 ;; esac
  return 1
}

watchdog_run_active() {
  local run_dir="$1" pid unit
  [[ -n "$run_dir" && -d "$run_dir" ]] || return 1
  if [[ -s "$run_dir/pid" ]]; then
    pid="$(head -n 1 "$run_dir/pid" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]] && pid_is_watchdog_process "$pid" "$run_dir"; then return 0; fi
  fi
  if [[ -s "$run_dir/unit" ]] && command -v systemctl >/dev/null 2>&1; then
    unit="$(head -n 1 "$run_dir/unit" 2>/dev/null || true)"
    if [[ -n "$unit" ]] && systemctl --user is-active --quiet "$unit" 2>/dev/null; then return 0; fi
  fi
  return 1
}

spawn_recovery() {
  local reason="$1" active_count="${2:-0}" latest_run="${3-}" now last_spawn run_id run_dir runner unit launcher_log safe_reason task_id
  now="$(date -u +%s)"
  last_spawn="$(normalize_uint "$(last_spawn_epoch)" 0)"
  if (( now - last_spawn < MIN_SPAWN_INTERVAL_SECONDS )); then
    emit_event "spawn_suppressed" "minimum spawn interval active; reason=$reason"
    write_health "degraded" "spawn suppressed by minimum interval: $reason" "$active_count" "$latest_run"
    return 0
  fi
  if ! command -v codex >/dev/null 2>&1; then
    write_health "blocked" "codex CLI not found; cannot spawn recovery agent" "$active_count" "$latest_run"
    write_incident "codex-cli-missing" "$active_count" "$latest_run"
    return 1
  fi
  if [[ ! -x "$RALPH_ENTRYPOINT" ]]; then
    write_health "blocked" "Ralph entrypoint missing or not executable: $RALPH_ENTRYPOINT" "$active_count" "$latest_run"
    write_incident "ralph-entrypoint-missing" "$active_count" "$latest_run"
    return 1
  fi

  safe_reason="$(printf '%s' "$reason" | tr '[:upper:]_' '[:lower:]-' | sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//')"
  safe_reason="${safe_reason:-recovery}"
  run_id="$(date -u +%Y%m%dT%H%M%SZ)-$safe_reason"
  run_dir="$RUNS_DIR/$run_id"
  task_id="T-$(date -u +%Y-%m-%d)-watchdog-${safe_reason:0:54}"
  mkdir -p "$run_dir"

  {
    printf '{\n'
    printf '  "run_id": "%s",\n' "$(json_escape "$run_id")"
    printf '  "trigger": "%s",\n' "$(json_escape "$reason")"
    printf '  "created_at": "%s",\n' "$(ts)"
    printf '  "repo_root": "%s",\n' "$(json_escape "$REPO_ROOT")"
    printf '  "plan_file": "%s",\n' "$(json_escape "$PLAN_FILE")"
    printf '  "ralph_entrypoint": "%s",\n' "$(json_escape "$RALPH_ENTRYPOINT")"
    printf '  "task_id": "%s"\n' "$(json_escape "$task_id")"
    printf '}\n'
  } >"$run_dir/metadata.json"

  runner="$run_dir/run.sh"
  {
    printf '#!/usr/bin/env bash\n'
    printf 'set -Eeuo pipefail\n'
    printf 'export PATH=%s\n' "$(shell_quote "$PATH")"
    printf 'export RALPH_MODEL=%s\n' "$(shell_quote "${RALPH_WATCHDOG_MODEL:-${CODEX_MODEL:-}}")"
    printf 'export RALPH_REASONING_EFFORT=%s\n' "$(shell_quote "${RALPH_WATCHDOG_REASONING_EFFORT:-${CODEX_REASONING_EFFORT:-xhigh}}")"
    printf 'export RALPH_BYPASS_SANDBOX=%s\n' "$(shell_quote "${RALPH_WATCHDOG_BYPASS_SANDBOX:-true}")"
    printf 'export RALPH_RUNTIME_ROOT=%s\n' "$(shell_quote "$run_dir/ralph")"
    printf 'cd %s\n' "$(shell_quote "$REPO_ROOT")"
    printf 'exec %s --execute --task-id %s --plan-file %s --task %s >> %s 2>> %s\n' \
      "$(shell_quote "$RALPH_ENTRYPOINT")" "$(shell_quote "$task_id")" "$(shell_quote "$PLAN_FILE")" \
      "$(shell_quote "Watchdog trigger: $reason. Advance one implementation-plan item through the Ralph workflow.")" \
      "$(shell_quote "$run_dir/events.jsonl")" "$(shell_quote "$run_dir/stderr.log")"
  } >"$runner"
  chmod 700 "$runner"

  launcher_log="$run_dir/launcher.log"
  unit="ralph-checklist-${run_id//[^A-Za-z0-9]/-}"
  if command -v systemd-run >/dev/null 2>&1 \
    && command -v systemctl >/dev/null 2>&1 \
    && systemctl --user show-environment >/dev/null 2>&1 \
    && systemd-run --user --collect --unit="$unit" --working-directory="$REPO_ROOT" "$runner" >>"$launcher_log" 2>&1; then
    printf '%s\n' "$unit" >"$run_dir/unit"
    emit_event "spawned" "systemd-run unit=$unit reason=$reason run=$run_dir"
  else
    nohup "$runner" >/dev/null 2>>"$launcher_log" &
    printf '%s\n' "$!" >"$run_dir/pid"
    emit_event "spawned" "nohup pid=$! reason=$reason run=$run_dir"
  fi

  ln -sfn "$run_dir" "$RUNTIME_ROOT/current-run"
  mark_spawn_epoch
  write_health "spawned" "$reason" "$active_count" "$run_dir"
}

if [[ "${RALPH_WATCHDOG_ENABLED:-true}" != "true" ]]; then
  emit_event "disabled" "RALPH_WATCHDOG_ENABLED is not true"
  write_health "disabled" "env toggle disabled" "0" ""
  exit 0
fi
if [[ ! -f "$REPO_ROOT/$PLAN_FILE" ]]; then
  write_health "blocked" "plan file missing: $REPO_ROOT/$PLAN_FILE" "0" ""
  write_incident "plan-file-missing" "0" ""
  exit 1
fi

tmp_agents="$ACTIVE_AGENTS_FILE.tmp"
find_active_agents >"$tmp_agents"
mv "$tmp_agents" "$ACTIVE_AGENTS_FILE"
active_count="$(normalize_uint "$(wc -l <"$ACTIVE_AGENTS_FILE" | tr -d ' ')" 0)"
latest_run="$(latest_run_dir)"

if watchdog_run_active "$latest_run"; then
  before_size="$(run_output_size "$latest_run")"
  sleep "$PROBE_SECONDS"
  after_size="$(run_output_size "$latest_run")"
  if (( after_size > before_size )); then
    emit_event "healthy" "watchdog-owned output advanced ${before_size}->${after_size}; active agent count=$active_count"
    write_health "healthy" "watchdog-owned agent output advanced" "$active_count" "$latest_run"
    exit 0
  fi
  write_incident "watchdog-output-stalled" "$active_count" "$latest_run"
  now="$(date -u +%s)"
  last_spawn="$(normalize_uint "$(last_spawn_epoch)" 0)"
  if (( now - last_spawn >= STALL_RECOVERY_COOLDOWN_SECONDS )); then
    spawn_recovery "watchdog-output-stalled" "$active_count" "$latest_run"
  else
    emit_event "stall_recovery_suppressed" "cooldown active; active agent count=$active_count latest_run=$latest_run"
    write_health "degraded" "watchdog-owned output stalled; recovery suppressed by cooldown" "$active_count" "$latest_run"
  fi
  exit 0
fi

if (( active_count == 0 )); then
  dirty_status="$(worktree_status)"
  if [[ -n "$dirty_status" && "${RALPH_WATCHDOG_ALLOW_DIRTY_WORKTREE:-false}" != "true" ]]; then
    printf '%s\n' "$dirty_status" >"$RUNTIME_ROOT/worktree-status.txt"
    write_health "blocked" "worktree has uncommitted changes; refusing to spawn Ralph" "0" "$latest_run"
    write_incident "dirty-worktree" "0" "$latest_run"
    exit 0
  fi
  write_incident "no-active-agent" "0" "$latest_run"
  spawn_recovery "no-active-agent" "0" "$latest_run"
  exit 0
fi

emit_event "healthy" "manual or external repo agent active count=$active_count"
write_health "healthy" "manual or external repo agent is active" "$active_count" "$latest_run"

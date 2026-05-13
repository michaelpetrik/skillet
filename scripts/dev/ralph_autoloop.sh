#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${RALPH_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"
PLAN_FILE="${RALPH_PLAN_FILE:-docs/REFACTOR_PLAN.md}"
RUNTIME_ROOT="${RALPH_AUTOLOOP_RUNTIME_ROOT:-$REPO_ROOT/var/dev/ralph-autoloop}"
CHECKLIST_ENTRYPOINT="${RALPH_AUTOLOOP_CHECKLIST_ENTRYPOINT:-$REPO_ROOT/scripts/dev/ralph_checklist.sh}"
QUALITY_COMMAND="${RALPH_AUTOLOOP_QUALITY_COMMAND:-scripts/ci/run_quality_gates.sh}"
TASK_TEXT="Advance Skillet refactor items continuously until blocked or complete."
TASK_ID_BASE="T-$(date -u +%Y-%m-%d)-ralph-autoloop"
EXECUTE=false
MAX_ITERATIONS="${RALPH_AUTOLOOP_MAX_ITERATIONS:-6}"
PUSH_CHANGES="${RALPH_AUTOLOOP_PUSH:-true}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/dev/ralph_autoloop.sh [options]

Options:
  --task TEXT             High-level goal for this autoloop run.
  --task-id ID            Stable task id base. Default: T-<utc-date>-ralph-autoloop.
  --plan-file PATH        Plan/checklist path relative to repo root.
  --execute               Run checklist workers. Without this, only writes run artifacts.
  --quality-command CMD   Quality command to run before/after worker iterations.
  --no-quality            Disable quality command.
  --runtime-root DIR      Artifact root. Default: var/dev/ralph-autoloop.
  --max-iterations N      Max checklist iterations in this supervisor run. Default: 6.
  --no-push               Do not push clean committed changes to the upstream branch.
  -h, --help              Show help.
USAGE
}

while (($#)); do
  case "$1" in
    --task)
      [[ $# -ge 2 ]] || { printf 'missing value for --task\n' >&2; exit 64; }
      TASK_TEXT="$2"
      shift 2
      ;;
    --task-id)
      [[ $# -ge 2 ]] || { printf 'missing value for --task-id\n' >&2; exit 64; }
      TASK_ID_BASE="$2"
      shift 2
      ;;
    --plan-file)
      [[ $# -ge 2 ]] || { printf 'missing value for --plan-file\n' >&2; exit 64; }
      PLAN_FILE="${2#./}"
      shift 2
      ;;
    --execute)
      EXECUTE=true
      shift
      ;;
    --quality-command)
      [[ $# -ge 2 ]] || { printf 'missing value for --quality-command\n' >&2; exit 64; }
      QUALITY_COMMAND="$2"
      shift 2
      ;;
    --no-quality)
      QUALITY_COMMAND=""
      shift
      ;;
    --runtime-root)
      [[ $# -ge 2 ]] || { printf 'missing value for --runtime-root\n' >&2; exit 64; }
      RUNTIME_ROOT="$2"
      shift 2
      ;;
    --max-iterations)
      [[ $# -ge 2 ]] || { printf 'missing value for --max-iterations\n' >&2; exit 64; }
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --no-push)
      PUSH_CHANGES=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 64
      ;;
  esac
done

case "$MAX_ITERATIONS" in
  ''|*[!0-9]*) printf 'max iterations must be a positive integer: %s\n' "$MAX_ITERATIONS" >&2; exit 64 ;;
esac
if (( MAX_ITERATIONS < 1 )); then
  printf 'max iterations must be at least 1\n' >&2
  exit 64
fi

if [[ ! -f "$REPO_ROOT/$PLAN_FILE" ]]; then
  printf 'plan file missing: %s\n' "$REPO_ROOT/$PLAN_FILE" >&2
  exit 1
fi
if [[ ! -x "$CHECKLIST_ENTRYPOINT" ]]; then
  printf 'checklist entrypoint missing or not executable: %s\n' "$CHECKLIST_ENTRYPOINT" >&2
  exit 1
fi
if ! git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf 'not a git worktree: %s\n' "$REPO_ROOT" >&2
  exit 1
fi

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
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

safe_task_suffix() {
  local value="$1"
  value="$(printf '%s' "$value" | tr '[:upper:]_' '[:lower:]-' | sed 's/[^a-z0-9-]/-/g; s/--*/-/g; s/^-//; s/-$//')"
  printf '%s' "${value:-ralph-autoloop}"
}

worktree_status() {
  git -C "$REPO_ROOT" status --short --untracked-files=all
}

require_clean_worktree() {
  local status_file="$1" status
  status="$(worktree_status)"
  printf '%s\n' "$status" >"$status_file"
  [[ -z "$status" ]]
}

plan_has_actionable_items() {
  awk -F'|' '
    $2 ~ / R[0-9]+ / && $3 ~ /\[( |~)\]/ { found = 1 }
    END { exit found ? 0 : 1 }
  ' "$REPO_ROOT/$PLAN_FILE"
}

write_status() {
  local state="$1" reason="$2" iteration="$3" head="$4" tmp="$STATUS_FILE.tmp"
  {
    printf '{\n'
    printf '  "ts": "%s",\n' "$(ts)"
    printf '  "state": "%s",\n' "$(json_escape "$state")"
    printf '  "reason": "%s",\n' "$(json_escape "$reason")"
    printf '  "iteration": %s,\n' "$iteration"
    printf '  "max_iterations": %s,\n' "$MAX_ITERATIONS"
    printf '  "head": "%s",\n' "$(json_escape "$head")"
    printf '  "task": "%s",\n' "$(json_escape "$TASK_TEXT")"
    printf '  "plan_file": "%s",\n' "$(json_escape "$PLAN_FILE")"
    printf '  "run_dir": "%s",\n' "$(json_escape "$RUN_DIR")"
    printf '  "events_file": "%s",\n' "$(json_escape "$EVENTS_FILE")"
    printf '  "quality_command": "%s",\n' "$(json_escape "$QUALITY_COMMAND")"
    printf '  "push_changes": "%s"\n' "$(json_escape "$PUSH_CHANGES")"
    printf '}\n'
  } >"$tmp"
  mv "$tmp" "$STATUS_FILE"
}

emit_event() {
  printf '{"ts":"%s","event":"%s","message":"%s"}\n' \
    "$(ts)" "$(json_escape "$1")" "$(json_escape "${2-}")" >>"$EVENTS_FILE"
}

run_quality() {
  local iteration_dir="$1"
  [[ -n "$QUALITY_COMMAND" ]] || return 0
  (cd "$REPO_ROOT" && bash -lc "$QUALITY_COMMAND") >"$iteration_dir/quality.stdout" 2>"$iteration_dir/quality.stderr"
}

sync_upstream() {
  local iteration_dir="$1" upstream remote ahead behind
  upstream="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
  [[ -n "$upstream" ]] || return 0

  remote="${upstream%%/*}"
  git -C "$REPO_ROOT" fetch --quiet "$remote" >"$iteration_dir/git-fetch.stdout" 2>"$iteration_dir/git-fetch.stderr"

  behind="$(git -C "$REPO_ROOT" rev-list --count "HEAD..$upstream")"
  if (( behind > 0 )); then
    printf 'upstream %s is ahead by %s commit(s); refusing automatic rebase in autoloop\n' "$upstream" "$behind" \
      >"$iteration_dir/git-sync.blocked"
    return 7
  fi

  ahead="$(git -C "$REPO_ROOT" rev-list --count "$upstream..HEAD")"
  if (( ahead > 0 )); then
    git -C "$REPO_ROOT" push >"$iteration_dir/git-push.stdout" 2>"$iteration_dir/git-push.stderr"
  fi
}

mkdir -p "$RUNTIME_ROOT/runs"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(safe_task_suffix "$TASK_ID_BASE")"
RUN_DIR="$RUNTIME_ROOT/runs/$RUN_ID"
mkdir -p "$RUN_DIR"
ln -sfn "$RUN_DIR" "$RUNTIME_ROOT/current-run"

LOCK_FILE="$RUNTIME_ROOT/autoloop.lock"
EVENTS_FILE="$RUN_DIR/events.jsonl"
STATUS_FILE="$RUN_DIR/status.json"
LOG_FILE="$RUN_DIR/autoloop.log"
INITIAL_STATUS="$RUN_DIR/git-status.initial"
FINAL_STATUS="$RUN_DIR/git-status.final"

exec > >(tee -a "$LOG_FILE") 2>&1
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  printf '%s another Ralph autoloop is already running\n' "$(ts)"
  exit 0
fi

printf 'Ralph autoloop run: %s\n' "$RUN_DIR"
printf 'Plan: %s\n' "$PLAN_FILE"
printf 'Max iterations: %s\n' "$MAX_ITERATIONS"
printf 'Quality command: %s\n' "${QUALITY_COMMAND:-disabled}"
printf 'Push changes: %s\n' "$PUSH_CHANGES"

head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
write_status "prepared" "run artifacts created" "0" "$head_now"

if ! require_clean_worktree "$INITIAL_STATUS"; then
  emit_event "blocked" "dirty worktree before autoloop start"
  write_status "blocked" "dirty worktree before autoloop start" "0" "$head_now"
  printf 'dirty worktree before autoloop start; see %s\n' "$INITIAL_STATUS" >&2
  exit 3
fi

if ! plan_has_actionable_items; then
  emit_event "complete" "no actionable plan items"
  write_status "complete" "no actionable plan items" "0" "$head_now"
  exit 0
fi

if [[ "$EXECUTE" != true ]]; then
  emit_event "prepared" "execute flag not set"
  printf '\nContinue with:\n'
  printf '  %s --execute --task-id %s --task %s --plan-file %s --max-iterations %s\n' \
    "$(shell_quote "$0")" "$(shell_quote "$TASK_ID_BASE")" "$(shell_quote "$TASK_TEXT")" \
    "$(shell_quote "$PLAN_FILE")" "$(shell_quote "$MAX_ITERATIONS")"
  exit 0
fi

for ((iteration = 1; iteration <= MAX_ITERATIONS; iteration += 1)); do
  if ! plan_has_actionable_items; then
    head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
    emit_event "complete" "no actionable plan items before iteration $iteration"
    write_status "complete" "no actionable plan items" "$((iteration - 1))" "$head_now"
    break
  fi

  iteration_dir="$RUN_DIR/iterations/$iteration"
  mkdir -p "$iteration_dir"
  if ! require_clean_worktree "$iteration_dir/git-status.before"; then
    head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
    emit_event "blocked" "dirty worktree before iteration $iteration"
    write_status "blocked" "dirty worktree before iteration $iteration" "$iteration" "$head_now"
    exit 3
  fi

  head_before="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  iteration_task_id="T-$(date -u +%Y-%m-%d)-autoloop-i$(printf '%02d' "$iteration")"
  iteration_task="Autoloop iteration $iteration/$MAX_ITERATIONS. Advance the first actionable item in $PLAN_FILE, commit all intended changes, and leave the worktree clean. Do not ask the user for next steps; TODO is a machine handoff for the supervisor."
  emit_event "iteration_started" "$iteration_task_id head=$head_before"
  write_status "running" "iteration $iteration running" "$iteration" "$head_before"

  checklist_args=(
    --execute
    --task-id "$iteration_task_id"
    --plan-file "$PLAN_FILE"
    --task "$iteration_task"
    --runtime-root "$iteration_dir/ralph"
  )
  if [[ -n "$QUALITY_COMMAND" ]]; then
    checklist_args+=(--quality-command "$QUALITY_COMMAND")
  else
    checklist_args+=(--no-quality)
  fi

  set +e
  "$CHECKLIST_ENTRYPOINT" "${checklist_args[@]}" >"$iteration_dir/ralph.stdout" 2>"$iteration_dir/ralph.stderr"
  status=$?
  set -e
  if (( status != 0 )); then
    head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
    require_clean_worktree "$iteration_dir/git-status.after" || true
    emit_event "blocked" "checklist iteration $iteration failed with exit $status"
    write_status "blocked" "checklist iteration $iteration failed with exit $status" "$iteration" "$head_now"
    exit "$status"
  fi

  if ! require_clean_worktree "$iteration_dir/git-status.after"; then
    head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
    emit_event "blocked" "checklist iteration $iteration left dirty worktree"
    write_status "blocked" "checklist iteration $iteration left dirty worktree" "$iteration" "$head_now"
    exit 3
  fi

  head_after="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  if [[ "$head_after" == "$head_before" ]]; then
    emit_event "blocked" "iteration $iteration made no commit"
    write_status "blocked" "iteration $iteration made no commit" "$iteration" "$head_after"
    exit 5
  fi

  set +e
  run_quality "$iteration_dir"
  status=$?
  set -e
  if (( status != 0 )); then
    emit_event "blocked" "post-iteration quality failed with exit $status"
    write_status "blocked" "post-iteration quality failed with exit $status" "$iteration" "$head_after"
    exit "$status"
  fi

  if [[ "$PUSH_CHANGES" == true ]]; then
    set +e
    sync_upstream "$iteration_dir"
    status=$?
    set -e
    if (( status != 0 )); then
      head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
      require_clean_worktree "$iteration_dir/git-status.after-sync" || true
      emit_event "blocked" "upstream sync failed with exit $status"
      write_status "blocked" "upstream sync failed with exit $status" "$iteration" "$head_now"
      exit "$status"
    fi
  fi

  if ! require_clean_worktree "$iteration_dir/git-status.after-sync"; then
    head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
    emit_event "blocked" "iteration $iteration sync left dirty worktree"
    write_status "blocked" "iteration $iteration sync left dirty worktree" "$iteration" "$head_now"
    exit 3
  fi

  head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  emit_event "iteration_completed" "$iteration_task_id head=$head_now"
  write_status "running" "iteration $iteration completed" "$iteration" "$head_now"
done

head_now="$(git -C "$REPO_ROOT" rev-parse HEAD)"
require_clean_worktree "$FINAL_STATUS" || {
  emit_event "blocked" "dirty worktree at autoloop end"
  write_status "blocked" "dirty worktree at autoloop end" "$MAX_ITERATIONS" "$head_now"
  exit 3
}

if plan_has_actionable_items; then
  emit_event "paused" "max iterations reached with actionable plan items remaining"
  write_status "paused" "max iterations reached with actionable plan items remaining" "$MAX_ITERATIONS" "$head_now"
else
  emit_event "complete" "no actionable plan items remain"
  write_status "complete" "no actionable plan items remain" "$MAX_ITERATIONS" "$head_now"
fi

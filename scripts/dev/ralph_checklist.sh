#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${RALPH_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"
PLAN_FILE="${RALPH_PLAN_FILE:-docs/REFACTOR_PLAN.md}"
RUNTIME_ROOT="${RALPH_RUNTIME_ROOT:-$REPO_ROOT/var/dev/ralph-checklist}"
TASK_ID="T-$(date -u +%Y-%m-%d)-ralph-dev"
TASK_TEXT="Advance the first unchecked Skillet refactor item without reverting user edits."
EXECUTE=false
AGENT="${RALPH_AGENT:-auto}"
MODEL="${RALPH_MODEL:-${CODEX_MODEL:-}}"
REASONING_EFFORT="${RALPH_REASONING_EFFORT:-${CODEX_REASONING_EFFORT:-xhigh}}"
SANDBOX_MODE="${RALPH_SANDBOX:-danger-full-access}"
BYPASS_SANDBOX="${RALPH_BYPASS_SANDBOX:-false}"
QUALITY_COMMAND="${RALPH_QUALITY_COMMAND:-}"
RUN_QUALITY=true

usage() {
  cat <<'USAGE'
Usage:
  scripts/dev/ralph_checklist.sh [options]

Options:
  --task TEXT             Work item or goal for this Ralph iteration.
  --task-id ID            Stable task id. Default: T-<utc-date>-ralph-dev.
  --plan-file PATH        Plan/checklist path relative to repo root.
  --execute               Launch Codex after writing run artifacts.
  --agent auto|codex|none Fallback worker selector. Default: auto.
  --quality-command CMD   Optional smoke/quality command to run before prompting.
  --no-quality            Skip quality command/preflight.
  --runtime-root DIR      Artifact root. Default: var/dev/ralph-checklist.
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
      TASK_ID="$2"
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
    --agent)
      [[ $# -ge 2 ]] || { printf 'missing value for --agent\n' >&2; exit 64; }
      AGENT="$2"
      shift 2
      ;;
    --quality-command)
      [[ $# -ge 2 ]] || { printf 'missing value for --quality-command\n' >&2; exit 64; }
      QUALITY_COMMAND="$2"
      RUN_QUALITY=true
      shift 2
      ;;
    --no-quality)
      RUN_QUALITY=false
      shift
      ;;
    --runtime-root)
      [[ $# -ge 2 ]] || { printf 'missing value for --runtime-root\n' >&2; exit 64; }
      RUNTIME_ROOT="$2"
      shift 2
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

case "$AGENT" in
  auto|codex|none) ;;
  *) printf 'unsupported --agent: %s (valid: auto, codex, none)\n' "$AGENT" >&2; exit 64 ;;
esac

if [[ ! "$TASK_ID" =~ ^T-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]{1,64}$ ]]; then
  printf 'task id must match ^T-YYYY-MM-DD-[a-z0-9-]{1,64}$: %s\n' "$TASK_ID" >&2
  exit 64
fi

if [[ ! -f "$REPO_ROOT/$PLAN_FILE" ]]; then
  printf 'plan file missing: %s\n' "$REPO_ROOT/$PLAN_FILE" >&2
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

mkdir -p "$RUNTIME_ROOT/runs"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$TASK_ID"
RUN_DIR="$RUNTIME_ROOT/runs/$RUN_ID"
mkdir -p "$RUN_DIR"
ln -sfn "$RUN_DIR" "$RUNTIME_ROOT/current-run"

STATUS_FILE="$RUN_DIR/status.json"
PROMPT_FILE="$RUN_DIR/prompt.md"
QUALITY_STDOUT="$RUN_DIR/quality.stdout"
QUALITY_STDERR="$RUN_DIR/quality.stderr"
GIT_STATUS_BEFORE="$RUN_DIR/git-status.before"
GIT_STATUS_AFTER="$RUN_DIR/git-status.after"
CODEX_STDOUT="$RUN_DIR/codex-events.jsonl"
CODEX_STDERR="$RUN_DIR/codex-stderr.log"
CODEX_FINAL="$RUN_DIR/codex-final.md"

codex_path="$(command -v codex || true)"
quality_status="skipped"
quality_reason="no quality command configured"
quality_exit=""

if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$REPO_ROOT" status --short --untracked-files=all >"$GIT_STATUS_BEFORE"
else
  printf 'not a git worktree\n' >"$GIT_STATUS_BEFORE"
fi

if [[ "$RUN_QUALITY" == true && -n "$QUALITY_COMMAND" ]]; then
  quality_status="running"
  quality_reason="running configured quality command"
  if (cd "$REPO_ROOT" && bash -lc "$QUALITY_COMMAND") >"$QUALITY_STDOUT" 2>"$QUALITY_STDERR"; then
    quality_status="passed"
    quality_reason="quality command passed"
    quality_exit="0"
  else
    quality_exit="$?"
    quality_status="failed"
    quality_reason="quality command failed; see quality.stderr"
  fi
elif [[ "$RUN_QUALITY" != true ]]; then
  quality_reason="disabled by --no-quality"
fi

{
  printf '# Ralph Checklist Worker\n\n'
  printf 'You are working in `%s`.\n\n' "$REPO_ROOT"
  printf 'Task id: `%s`\n' "$TASK_ID"
  printf 'Goal: %s\n' "$TASK_TEXT"
  printf 'Plan source of truth: `%s`\n\n' "$PLAN_FILE"
  printf 'Required workflow:\n\n'
  printf '1. Read `AGENTS.md` first if it exists.\n'
  printf '2. Read `%s` before planning or claiming completion.\n' "$PLAN_FILE"
  printf '3. Run `git status --short --untracked-files=all` and compare it with `%s` before editing.\n' "$GIT_STATUS_BEFORE"
  printf '4. If the worktree is dirty before you start, do not begin a new plan item. Verify and commit existing plan-related changes first, or stop as blocked if the dirty paths are unrelated, unsafe, or ambiguous.\n'
  printf '5. Pick one highest-priority open item that can be advanced safely.\n'
  printf '6. Make the smallest useful code, test, documentation, or automation change.\n'
  printf '7. Run the strongest available verification. If blocked, record exact commands and errors.\n'
  printf '8. Update `%s` only when status actually changes and evidence supports it.\n' "$PLAN_FILE"
  printf '9. Do not use destructive git commands, do not stash unfinished work, and do not revert unrelated edits.\n'
  printf '10. Keep changes scoped to the selected item.\n'
  printf '11. Commit every intended change before final handoff with a concise descriptive message tied to the plan item.\n'
  printf '12. Confirm `git status --short --untracked-files=all` is clean after the commit. If it is not clean, do not claim completion.\n\n'
  printf '13. Every smith/worker involved in the run must leave a concise handoff with two checklists:\n'
  printf '   - Done: completed changes and verification evidence.\n'
  printf '   - TODO: remaining work, blockers, and exact next commands.\n\n'
  printf 'Preflight:\n\n'
  printf -- '- Quality status: %s\n' "$quality_status"
  printf -- '- Quality reason: %s\n' "$quality_reason"
  printf -- '- Codex: %s\n' "${codex_path:-not found}"
  printf -- '- Run artifacts: `%s`\n' "$RUN_DIR"
  printf -- '- Initial git status artifact: `%s`\n\n' "$GIT_STATUS_BEFORE"
  printf 'Final answer must include changed files, verification results, final clean worktree evidence, next blocker, and the smith checklist.\n'
} >"$PROMPT_FILE"

{
  printf '{\n'
  printf '  "ts": "%s",\n' "$(ts)"
  printf '  "task_id": "%s",\n' "$(json_escape "$TASK_ID")"
  printf '  "task": "%s",\n' "$(json_escape "$TASK_TEXT")"
  printf '  "plan_file": "%s",\n' "$(json_escape "$PLAN_FILE")"
  printf '  "run_dir": "%s",\n' "$(json_escape "$RUN_DIR")"
  printf '  "prompt_file": "%s",\n' "$(json_escape "$PROMPT_FILE")"
  printf '  "codex": "%s",\n' "$(json_escape "${codex_path:-}")"
  printf '  "quality_command": "%s",\n' "$(json_escape "$QUALITY_COMMAND")"
  printf '  "quality_status": "%s",\n' "$(json_escape "$quality_status")"
  printf '  "quality_reason": "%s",\n' "$(json_escape "$quality_reason")"
  printf '  "quality_exit": "%s",\n' "$(json_escape "$quality_exit")"
  printf '  "git_status_before": "%s",\n' "$(json_escape "$GIT_STATUS_BEFORE")"
  printf '  "git_status_after": "%s"\n' "$(json_escape "$GIT_STATUS_AFTER")"
  printf '}\n'
} >"$STATUS_FILE"

if [[ "$AGENT" == auto ]]; then
  if [[ -n "$codex_path" ]]; then AGENT="codex"; else AGENT="none"; fi
fi

printf 'Ralph checklist run: %s\n' "$RUN_DIR"
printf 'Preflight: %s (%s)\n' "$quality_status" "$quality_reason"
printf 'Prompt: %s\n' "$PROMPT_FILE"
printf 'Status: %s\n' "$STATUS_FILE"

if [[ "$EXECUTE" != true ]]; then
  if [[ "$AGENT" == codex ]]; then
    printf '\nContinue with:\n'
    printf '  %s --execute --task-id %s --task %s --plan-file %s\n' \
      "$(shell_quote "$0")" "$(shell_quote "$TASK_ID")" "$(shell_quote "$TASK_TEXT")" "$(shell_quote "$PLAN_FILE")"
  fi
  exit 0
fi

if [[ "$AGENT" == none ]]; then
  printf 'No fallback agent selected; prompt is ready at %s\n' "$PROMPT_FILE" >&2
  exit 2
fi
if [[ "$AGENT" == codex && -z "$codex_path" ]]; then
  printf 'codex CLI not found; prompt is ready at %s\n' "$PROMPT_FILE" >&2
  exit 2
fi

export CODEX_REASONING_EFFORT="$REASONING_EFFORT"
codex_args=(exec --cd "$REPO_ROOT")
if [[ "$BYPASS_SANDBOX" == true ]]; then
  codex_args+=(--dangerously-bypass-approvals-and-sandbox)
else
  codex_args+=(--sandbox "$SANDBOX_MODE")
fi
if [[ -n "$MODEL" ]]; then
  codex_args+=(-m "$MODEL")
fi
codex_args+=(--json -o "$CODEX_FINAL" -)

set +e
codex "${codex_args[@]}" <"$PROMPT_FILE" >>"$CODEX_STDOUT" 2>>"$CODEX_STDERR"
codex_exit="$?"
set -e

if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git -C "$REPO_ROOT" status --short --untracked-files=all >"$GIT_STATUS_AFTER"
else
  printf 'not a git worktree\n' >"$GIT_STATUS_AFTER"
fi

if [[ -s "$GIT_STATUS_AFTER" ]]; then
  printf 'Ralph worker left uncommitted changes; see %s\n' "$GIT_STATUS_AFTER" >&2
  exit 3
fi

exit "$codex_exit"

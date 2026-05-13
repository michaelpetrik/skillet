#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${SKILLET_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"
MODE="changed"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci/secret_scan.sh [--changed|--all]

Options:
  --changed   Scan staged additions, unstaged additions, and untracked files. Default.
  --all       Scan tracked and untracked text files.
  -h, --help  Show help.

The scanner reports file paths, line numbers, and finding types only. It does not
print matching secret values.
USAGE
}

while (($#)); do
  case "$1" in
    --changed)
      MODE="changed"
      shift
      ;;
    --all)
      MODE="all"
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

cd "$REPO_ROOT"

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/skillet-secret-scan.XXXXXX")"
findings="$tmp_dir/findings.txt"
awk_program="$tmp_dir/secret-scan.awk"
trap 'rm -rf "$tmp_dir"' EXIT
: >"$findings"

cat >"$awk_program" <<'AWK'
function credential_assignment(line, lowered, key, value, compact) {
  if (line !~ /[:=]/) return ""

  key = lowered
  sub(/[:=].*/, "", key)
  gsub(/^[[:space:]"'`-]+/, "", key)
  gsub(/[[:space:]"'`]+$/, "", key)

  value = line
  sub(/^[^:=]*[:=][[:space:]]*/, "", value)
  compact = value
  gsub(/^[[:space:]"'`]+/, "", compact)
  gsub(/[[:space:]"'`,;]+$/, "", compact)

  if (length(compact) < 16) return ""
  if (tolower(compact) ~ /^(example|sample|dummy|placeholder|changeme|change-me|redacted|not-a-secret|fake|fixture)/) return ""
  if (compact !~ /^[A-Za-z0-9_+\/=:@.%~-]+$/) return ""

  if (key ~ /(^|[^a-z0-9])(api[_-]?key|access[_-]?key|secret|client[_-]?secret|password|passwd|private[_-]?key|auth[_-]?token|bearer[_-]?token|refresh[_-]?token|session[_-]?token|token)$/) {
    return "credential assignment"
  }

  return ""
}

function classify(line, lowered, kind) {
  lowered = tolower(line)

  if (line ~ /^[[:space:]]*$/) return ""
  if (line ~ /^[[:space:]]*(#|\/\/|\*|\/\*)/) return ""
  if (lowered ~ /(example|sample|dummy|placeholder|changeme|change-me|redacted|not-a-secret|fake|fixture)/) return ""

  if (line ~ /-----BEGIN [A-Z0-9 ]*(RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----/) return "private key block"
  if (line ~ /(AKIA|ASIA)[0-9A-Z]{16}/) return "AWS access key id"
  if (line ~ /github_pat_[A-Za-z0-9_]{22,}_[A-Za-z0-9_]{59,}/) return "GitHub fine-grained token"
  if (line ~ /gh[pousr]_[A-Za-z0-9_]{36,}/) return "GitHub token"
  if (line ~ /xox[baprs]-[A-Za-z0-9-]{20,}/) return "Slack token"
  if (line ~ /npm_[A-Za-z0-9]{36,}/) return "npm token"
  if (line ~ /sk-[A-Za-z0-9]{32,}/) return "OpenAI-style API key"
  kind = credential_assignment(line, lowered)
  if (kind != "") return kind

  return ""
}

function report(display, line_no, line, kind) {
  kind = classify(line)
  if (kind != "") {
    printf "%s:%d: %s\n", display, line_no, kind
  }
}

mode == "file" {
  report(display, FNR, $0)
  next
}

mode == "diff" && /^diff --git / {
  display = ""
  new_line = 0
  next
}

mode == "diff" && /^\+\+\+ / {
  display = substr($0, 5)
  if (display == "/dev/null") {
    display = ""
  } else if (display ~ /^b\//) {
    display = substr(display, 3)
  }
  next
}

mode == "diff" && /^@@ / {
  hunk = $0
  sub(/^@@ -[^ ]+ \+/, "", hunk)
  sub(/ .*/, "", hunk)
  split(hunk, parts, ",")
  new_line = parts[1] + 0
  if (new_line < 1) new_line = 1
  next
}

mode == "diff" && display != "" && substr($0, 1, 1) == "+" && substr($0, 1, 3) != "+++" {
  report(display, new_line, substr($0, 2))
  new_line += 1
  next
}
AWK

is_git_repo() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1
}

is_text_file() {
  local path="$1"
  [[ -f "$path" ]] || return 1
  grep -Iq . "$path" 2>/dev/null || [[ ! -s "$path" ]]
}

is_blocked_secret_path() {
  local path="${1#./}" base lower
  base="${path##*/}"
  lower="$(printf '%s' "$base" | tr '[:upper:]' '[:lower:]')"

  case "$lower" in
    .env|.env.*|*.pem|*.key|*.p12|*.pfx|*.jks|*.keystore|id_rsa|id_dsa|id_ecdsa|id_ed25519|*.agekey|*.gpg|*.asc)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

check_blocked_path() {
  local path="$1"
  if is_blocked_secret_path "$path"; then
    printf '%s: blocked secret-like file name\n' "$path" >>"$findings"
  fi
}

scan_file() {
  local path="$1"
  [[ -f "$path" ]] || return 0
  is_text_file "$path" || return 0
  awk -v mode="file" -v display="$path" -f "$awk_program" "$path" >>"$findings"
}

scan_diff() {
  local label="$1"
  shift
  printf 'secret scan: %s\n' "$label"
  git diff --no-color --no-ext-diff --unified=0 --diff-filter=ACMR "$@" -- . \
    | awk -v mode="diff" -f "$awk_program" >>"$findings"
}

scan_changed_paths() {
  git diff --name-only -z --diff-filter=ACMR "$@" -- . \
    | while IFS= read -r -d '' path; do
        check_blocked_path "$path"
      done
}

scan_untracked_files() {
  printf 'secret scan: untracked files\n'
  git ls-files --others --exclude-standard -z -- . \
    | while IFS= read -r -d '' path; do
        check_blocked_path "$path"
        scan_file "$path"
      done
}

scan_all_files() {
  printf 'secret scan: tracked and untracked files\n'
  git ls-files --cached --others --exclude-standard -z -- . \
    | while IFS= read -r -d '' path; do
        check_blocked_path "$path"
        scan_file "$path"
      done
}

scan_find_fallback() {
  printf 'secret scan: filesystem fallback\n'
  find . \
    \( -path './.git' -o -path './node_modules' -o -path './dist' -o -path './var' \) -prune -o \
    -type f -print0 \
    | while IFS= read -r -d '' path; do
        path="${path#./}"
        check_blocked_path "$path"
        scan_file "$path"
      done
}

if is_git_repo; then
  case "$MODE" in
    changed)
      scan_changed_paths --cached
      scan_changed_paths
      scan_diff "staged additions" --cached
      scan_diff "unstaged additions"
      scan_untracked_files
      ;;
    all)
      scan_all_files
      ;;
  esac
else
  scan_find_fallback
fi

if [[ -s "$findings" ]]; then
  printf '\nsecret scan failed; potential secrets were found (values omitted):\n' >&2
  sort -u "$findings" >&2
  exit 1
fi

printf 'secret scan passed\n'

#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${SKILLET_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"
SECRET_SCAN_MODE="all"
RUN_ADVISORY="${SKILLET_SECURITY_REVIEW_WITH_ADVISORY:-false}"
AUDIT_LEVEL="${NPM_AUDIT_LEVEL:-moderate}"

usage() {
  cat <<'USAGE'
Usage:
  scripts/ci/security_review.sh [options]

Options:
  --secret-scan MODE  Secret scan mode: all or changed. Default: all.
  --with-advisory    Run npm audit against the configured registry.
  --offline          Skip live registry advisory checks. Default.
  --audit-level LVL  npm audit level when --with-advisory is used. Default: moderate.
  -h, --help         Show help.

The local review always runs the repo-owned secret scanner first. Advisory checks
use npm registry data, so skipped advisory checks are reported as partial rather
than silently treated as complete security coverage.
USAGE
}

normalize_bool() {
  case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|y|on)
      printf 'true'
      ;;
    *)
      printf 'false'
      ;;
  esac
}

RUN_ADVISORY="$(normalize_bool "$RUN_ADVISORY")"

while (($#)); do
  case "$1" in
    --secret-scan)
      [[ $# -ge 2 ]] || { printf 'missing value for --secret-scan\n' >&2; exit 64; }
      SECRET_SCAN_MODE="$2"
      shift 2
      ;;
    --secret-scan=*)
      SECRET_SCAN_MODE="${1#*=}"
      shift
      ;;
    --with-advisory)
      RUN_ADVISORY=true
      shift
      ;;
    --offline|--no-advisory)
      RUN_ADVISORY=false
      shift
      ;;
    --audit-level)
      [[ $# -ge 2 ]] || { printf 'missing value for --audit-level\n' >&2; exit 64; }
      AUDIT_LEVEL="$2"
      shift 2
      ;;
    --audit-level=*)
      AUDIT_LEVEL="${1#*=}"
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

case "$SECRET_SCAN_MODE" in
  all|changed)
    ;;
  *)
    printf 'invalid --secret-scan value: %s\n' "$SECRET_SCAN_MODE" >&2
    exit 64
    ;;
esac

case "$AUDIT_LEVEL" in
  low|moderate|high|critical)
    ;;
  *)
    printf 'invalid --audit-level value: %s\n' "$AUDIT_LEVEL" >&2
    exit 64
    ;;
esac

run() {
  local label="$1"
  shift
  printf '\n==> %s\n' "$label"
  "$@"
}

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    printf 'required command not found: %s\n' "$name" >&2
    exit 127
  fi
}

cd "$REPO_ROOT"

run "secret scan ($SECRET_SCAN_MODE)" "$SCRIPT_DIR/secret_scan.sh" "--$SECRET_SCAN_MODE"

if [[ "$RUN_ADVISORY" == true ]]; then
  require_command npm
  if [[ ! -f package-lock.json && ! -f npm-shrinkwrap.json ]]; then
    printf 'npm advisory audit requires package-lock.json or npm-shrinkwrap.json\n' >&2
    exit 1
  fi
  run "npm advisory audit ($AUDIT_LEVEL)" npm audit "--audit-level=$AUDIT_LEVEL"
  printf '\nsecurity review passed\n'
else
  printf '\n==> partial: npm advisory audit skipped; pass --with-advisory to use live registry data\n'
  printf '\nsecurity review passed (partial: advisory audit skipped)\n'
fi

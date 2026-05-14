#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${SKILLET_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"

cd "$REPO_ROOT"

run() {
  printf '\n==> %s\n' "$*"
  "$@"
}

run "$SCRIPT_DIR/secret_scan.sh" --changed
run npm test

printf '\npre-commit gates passed\n'

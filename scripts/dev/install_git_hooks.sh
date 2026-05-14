#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${SKILLET_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"
HOOKS_DIR="$REPO_ROOT/.githooks"

cd "$REPO_ROOT"

if [[ ! -d "$HOOKS_DIR" ]]; then
  printf 'missing hooks directory: %s\n' "$HOOKS_DIR" >&2
  exit 1
fi

chmod +x "$HOOKS_DIR/pre-commit" "$HOOKS_DIR/pre-push" "$REPO_ROOT/scripts/ci/pre_commit.sh"
git config core.hooksPath .githooks

printf 'git hooks installed: core.hooksPath=.githooks\n'

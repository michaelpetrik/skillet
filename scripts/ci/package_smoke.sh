#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="${SKILLET_REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"

cd "$REPO_ROOT"

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/skillet-package-smoke.XXXXXX")"
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

require_entry() {
  local entry="$1" file_list="$2"
  if ! grep -Fx "$entry" "$file_list" >/dev/null; then
    printf 'package tarball is missing required file: %s\n' "$entry" >&2
    exit 1
  fi
}

run npm run build

pack_output="$tmp_dir/npm-pack.txt"
run_capture "npm pack" "$pack_output" npm pack --pack-destination "$tmp_dir"
tarball_name="$(tail -n 1 "$pack_output")"
tarball="$tmp_dir/$tarball_name"

if [[ ! -f "$tarball" ]]; then
  printf 'npm pack did not create expected tarball: %s\n' "$tarball" >&2
  cat "$pack_output" >&2
  exit 1
fi

tarball_files="$tmp_dir/tarball-files.txt"
run_capture "tarball file list" "$tarball_files" tar -tf "$tarball"

unexpected_files="$tmp_dir/unexpected-package-files.txt"
: >"$unexpected_files"
while IFS= read -r entry; do
  case "$entry" in
    package/package.json|package/README.md|package/AGENTS.md|package/dist|package/dist/*|package/skills|package/skills/*) ;;
    *) printf '%s\n' "$entry" >>"$unexpected_files" ;;
  esac
done <"$tarball_files"

if [[ -s "$unexpected_files" ]]; then
  printf 'package tarball includes unexpected files:\n' >&2
  sed 's/^/  /' "$unexpected_files" >&2
  exit 1
fi

require_entry "package/package.json" "$tarball_files"
require_entry "package/README.md" "$tarball_files"
require_entry "package/AGENTS.md" "$tarball_files"
require_entry "package/dist/cli.js" "$tarball_files"
require_entry "package/skills/README.md" "$tarball_files"

install_root="$tmp_dir/install"
project_root="$tmp_dir/project"
global_skills_root="$tmp_dir/global-skills"
mkdir -p "$install_root" "$project_root" "$global_skills_root"

run npm install --prefix "$install_root" --ignore-scripts --no-audit --no-fund "$tarball"

packaged_bin="$install_root/node_modules/.bin/skillet"
if [[ ! -x "$packaged_bin" ]]; then
  printf 'packaged skillet bin is not executable: %s\n' "$packaged_bin" >&2
  exit 1
fi

run_capture "packaged CLI help smoke" "$tmp_dir/skillet-help.txt" "$packaged_bin" --help
run_capture "packaged CLI list smoke" "$tmp_dir/skillet-list.json" \
  "$packaged_bin" list --json --project "$project_root" --global-dir "$global_skills_root"

node - "$tmp_dir/skillet-list.json" <<'NODE'
import fs from "node:fs";

const listPath = process.argv.at(-1);
const rows = JSON.parse(fs.readFileSync(listPath, "utf8"));

if (!Array.isArray(rows) || rows.length === 0) {
  throw new Error("packaged CLI list did not return catalog rows");
}

const names = new Set(rows.map((row) => row.name));
if (!names.has("repo-quality-guardrails")) {
  throw new Error("packaged CLI list did not load expected skills catalog");
}
NODE

printf '\npackage smoke passed: %s\n' "$tarball_name"

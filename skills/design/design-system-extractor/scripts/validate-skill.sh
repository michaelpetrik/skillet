#!/usr/bin/env bash
# validate-skill.sh — lint a skill directory.
#
# Checks:
#   1) SKILL.md exists.
#   2) Frontmatter is well-formed YAML between '---' fences.
#   3) `name` matches the skill folder name and is kebab-case.
#   4) `description` is 100..300 characters.
#   5) `category` is non-empty.
#   6) `version` is semver (X.Y.Z).
#   7) `allowed-tools` is a non-empty list.
#   8) Every relative markdown link in SKILL.md resolves to an existing file.
#
# Usage: bash validate-skill.sh <skill-dir>
# Exit:  0 on pass, 1 on any failure.

set -u

SKILL_DIR="${1:-}"
if [[ -z "$SKILL_DIR" ]]; then
  echo "Usage: $0 <skill-dir>" >&2
  exit 2
fi
if [[ ! -d "$SKILL_DIR" ]]; then
  echo "FAIL: not a directory: $SKILL_DIR" >&2
  exit 1
fi

SKILL_DIR="$(cd "$SKILL_DIR" && pwd)"
SKILL_MD="$SKILL_DIR/SKILL.md"
FOLDER_NAME="$(basename "$SKILL_DIR")"
FAIL=0

err() { echo "FAIL: $*"; FAIL=1; }
ok()  { echo "OK:   $*"; }

# 1) SKILL.md exists
if [[ ! -f "$SKILL_MD" ]]; then
  err "SKILL.md is missing in $SKILL_DIR"
  exit 1
fi
ok "SKILL.md present"

# 2) Frontmatter
HEAD="$(awk '
  NR==1 { if ($0 != "---") { exit 1 } else { in_fm=1; next } }
  in_fm==1 && $0=="---" { exit 0 }
  in_fm==1 { print }
' "$SKILL_MD" 2>/dev/null)"

if [[ -z "$HEAD" ]]; then
  err "No YAML frontmatter found at top of SKILL.md"
fi

field() {
  # Extract a top-level scalar field from frontmatter.
  awk -v key="$1" '
    $0 ~ "^"key":" {
      sub("^"key":[[:space:]]*","",$0)
      gsub(/^"|"$/,"",$0)
      gsub(/^'\''|'\''$/,"",$0)
      print
      exit
    }
  ' <<<"$HEAD"
}

NAME="$(field name)"
DESC="$(field description)"
CATEGORY="$(field category)"
VERSION="$(field version)"

# 3) Name match + kebab-case
if [[ -z "$NAME" ]]; then
  err "frontmatter 'name' is missing"
elif [[ "$NAME" != "$FOLDER_NAME" ]]; then
  err "frontmatter 'name' ($NAME) != folder name ($FOLDER_NAME)"
elif [[ ! "$NAME" =~ ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ ]]; then
  err "frontmatter 'name' ($NAME) is not kebab-case"
else
  ok "name matches folder & is kebab-case: $NAME"
fi

# 4) Description length
DESC_LEN=${#DESC}
if [[ -z "$DESC" ]]; then
  err "frontmatter 'description' is missing"
elif (( DESC_LEN < 100 )); then
  err "description is too short ($DESC_LEN chars; min 100)"
elif (( DESC_LEN > 1024 )); then
  err "description is too long ($DESC_LEN chars; max 1024)"
else
  ok "description length OK ($DESC_LEN chars)"
fi

# 5) Category
if [[ -z "$CATEGORY" ]]; then
  err "frontmatter 'category' is missing"
else
  ok "category: $CATEGORY"
fi

# 6) Version
if [[ -z "$VERSION" ]]; then
  err "frontmatter 'version' is missing"
elif [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  err "version ($VERSION) is not semver X.Y.Z"
else
  ok "version: $VERSION"
fi

# 7) allowed-tools list (non-empty)
TOOLS_BLOCK="$(awk '
  /^allowed-tools:/ { in_tools=1; next }
  in_tools==1 && /^[a-zA-Z_-]+:/ { exit }
  in_tools==1 { print }
' <<<"$HEAD")"
TOOL_COUNT="$(awk '/^[[:space:]]*-/{c++} END{print c+0}' <<<"$TOOLS_BLOCK")"
if (( TOOL_COUNT < 1 )); then
  err "allowed-tools is empty or missing"
else
  ok "allowed-tools entries: $TOOL_COUNT"
fi

# 8) Relative markdown link check
LINKS="$(grep -oE '\]\(([^)]+)\)' "$SKILL_MD" | sed -E 's/^\]\(//;s/\)$//' || true)"
BAD_LINKS=0
while IFS= read -r LINK; do
  [[ -z "$LINK" ]] && continue
  # Skip absolute http(s) and anchors
  case "$LINK" in
    http://*|https://*|mailto:*|"#"*) continue ;;
  esac
  PATH_PART="${LINK%%#*}"
  [[ -z "$PATH_PART" ]] && continue
  # Resolve relative to SKILL.md directory
  case "$PATH_PART" in
    /*) ABS="$PATH_PART" ;;
    *)  ABS="$SKILL_DIR/$PATH_PART" ;;
  esac
  if [[ ! -e "$ABS" ]]; then
    err "broken markdown link: $LINK"
    BAD_LINKS=$((BAD_LINKS+1))
  fi
done <<< "$LINKS"
if (( BAD_LINKS == 0 )); then
  ok "all relative markdown links resolve"
fi

if (( FAIL == 0 )); then
  echo
  echo "PASS: $SKILL_DIR"
  exit 0
else
  echo
  echo "FAILED: $SKILL_DIR"
  exit 1
fi

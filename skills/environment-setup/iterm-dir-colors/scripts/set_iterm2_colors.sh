#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  set_iterm2_colors.sh [--dir <path>] [--color <preset|#RRGGBB>] [--badge <text>]

Examples:
  set_iterm2_colors.sh
  set_iterm2_colors.sh --dir /path/to/repo --color ember
  set_iterm2_colors.sh --dir /path/to/repo --color '#7a2f3a'
EOF
}

target_dir="$PWD"
color_value=""
badge=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      target_dir="$2"
      shift 2
      ;;
    --color)
      color_value="$2"
      shift 2
      ;;
    --badge)
      badge="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "$target_dir" ]]; then
  echo "Target directory does not exist: $target_dir" >&2
  exit 1
fi

target_dir="$(cd "$target_dir" && pwd)"
folder_name="$(basename "$target_dir")"
if [[ -z "$badge" ]]; then
  badge="$folder_name"
fi

declare -a palettes=(
  "ember"
  "wine"
  "rust"
  "crimson"
  "aubergine"
  "forest"
  "ocean"
  "slate"
)

palette_background() {
  case "$1" in
    ember) echo "#3f2629" ;;
    wine) echo "#4a2434" ;;
    rust) echo "#5a2f24" ;;
    crimson) echo "#58232c" ;;
    aubergine) echo "#44263f" ;;
    forest) echo "#243a2d" ;;
    ocean) echo "#213947" ;;
    slate) echo "#2d3342" ;;
    *)
      return 1
      ;;
  esac
}

palette_foreground() {
  case "$1" in
    ember) echo "#f6e9e7" ;;
    wine) echo "#fae8f0" ;;
    rust) echo "#faece7" ;;
    crimson) echo "#f9e7eb" ;;
    aubergine) echo "#f3e8f6" ;;
    forest) echo "#e8f5ec" ;;
    ocean) echo "#e7f4f9" ;;
    slate) echo "#edf1f8" ;;
    *)
      return 1
      ;;
  esac
}

is_hex_color() {
  [[ "$1" =~ ^#[0-9A-Fa-f]{6}$ ]]
}

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

foreground_for_background() {
  local hex="${1#\#}"
  local r=$((16#${hex:0:2}))
  local g=$((16#${hex:2:2}))
  local b=$((16#${hex:4:2}))
  local yiq=$(((r * 299 + g * 587 + b * 114) / 1000))

  if (( yiq >= 140 )); then
    echo "#161112"
  else
    echo "#f7f2f1"
  fi
}

choose_palette() {
  local name="$1"
  local sum=0
  local i
  local ord

  for ((i = 0; i < ${#name}; i++)); do
    printf -v ord '%d' "'${name:i:1}"
    ((sum += ord))
  done

  echo "${palettes[sum % ${#palettes[@]}]}"
}

selected_palette=""
background=""
foreground=""

if [[ -n "$color_value" ]]; then
  if is_hex_color "$color_value"; then
    background="$(to_lower "$color_value")"
    foreground="$(foreground_for_background "$background")"
  else
    selected_palette="$(to_lower "$color_value")"
    background="$(palette_background "$selected_palette" || true)"
    foreground="$(palette_foreground "$selected_palette" || true)"
    if [[ -z "$background" || -z "$foreground" ]]; then
      echo "Unknown color preset: $color_value" >&2
      echo "Available presets: ${palettes[*]}" >&2
      exit 1
    fi
  fi
else
  selected_palette="$(choose_palette "$folder_name")"
  background="$(palette_background "$selected_palette")"
  foreground="$(palette_foreground "$selected_palette")"
fi

output_file="$target_dir/.iterm2-colors"
cat > "$output_file" <<EOF
BACKGROUND=$background
FOREGROUND=$foreground
BADGE=$badge
EOF

echo "Wrote $output_file"
if [[ -n "$selected_palette" ]]; then
  echo "PALETTE=$selected_palette"
fi
echo "BACKGROUND=$background"
echo "FOREGROUND=$foreground"
echo "BADGE=$badge"

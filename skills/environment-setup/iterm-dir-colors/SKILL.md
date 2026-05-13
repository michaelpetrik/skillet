---
name: iterm-dir-colors
description: Configure project-local iTerm2 directory colors by creating or updating `.iterm2-colors` files. Use when the user wants a repo or folder tinted in iTerm, wants a chosen or auto-picked color, prefers dark backgrounds, or wants badge text derived from the directory name.
category: Environment Setup
version: 1.0.0
---

# iTerm Directory Colors

Use this skill when the task is to add or update a folder-local `.iterm2-colors` file for iTerm.

The local shell setup already looks for the nearest `.iterm2-colors` file and reads:

- `BACKGROUND`
- `FOREGROUND`
- `BADGE`

## Defaults

- Prefer dark backgrounds.
- If no color is specified, pick a dark preset deterministically from the folder name.
- Badge defaults to the target folder name.

## Workflow

1. Choose the target folder. Default is the current directory.
2. If the user gave a color, use either a named preset from [references/palettes.md](./references/palettes.md) or a direct `#RRGGBB` background value.
3. If no color was provided, let the script auto-pick a dark preset from the folder name.
4. Run:

```bash
/Users/michal/.codex/skills/iterm-dir-colors/scripts/set_iterm2_colors.sh --dir "<target-dir>" [--color "<preset-or-hex>"]
```

5. Report the written file path and the final `BACKGROUND`, `FOREGROUND`, and `BADGE` values.

## Notes

- The script writes `<target-dir>/.iterm2-colors`.
- For direct hex colors, the script derives a readable foreground automatically.
- Use `--badge` only when the user explicitly wants badge text different from the folder name.


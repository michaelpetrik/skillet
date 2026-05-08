# Pencil MCP — Best Practices

Top 10 patterns for using `mcp__pencil__*` tools efficiently.

## Top 10

1. **`get_editor_state({ include_schema: true })` ONCE per session.** Cache the schema. Subsequent reads use `batch_get` with specific node IDs.
2. **Always `batch_get` over many singletons.** One call with N IDs >> N calls. Reuse the same call shape across regions.
3. **`set_variables` BEFORE creating components.** Variables (tokens) must exist first; components reference them by name. Reverse order = orphaned literals.
4. **Components MUST set `reusable: true` and a stable name.** Naming convention: `Atom/<Name>/<Variant>` (`Atom/Button/Primary`). Without this you get visual duplicates with no shared source.
5. **Use `placeholder: true` for slot content.** Lets downstream consumers swap content without breaking the reusable's structure.
6. **`get_screenshot` per section, not whole document.** Faster, more diff-friendly, avoids token burn.
7. **`snapshot_layout({ problemsOnly: true })` is the cheap layout linter.** Run before `get_screenshot` to fix overlap/overflow first.
8. **`find_empty_space_on_canvas` before placing a new frame.** Avoid colliding with existing artwork.
9. **`search_all_unique_properties({ property: "fill" })` audits hex literals.** Run after build — anything that's not a token reference is a leak.
10. **`replace_all_matching_properties` for bulk token migration.** Convert raw hex → token references in one pass instead of editing each node.

## Anti-patterns (don't)

- Polling `get_editor_state` after every edit → context blow-up; use `snapshot_layout` instead.
- Creating components individually with `batch_design` containing one node → batch them.
- Naming components by visual appearance (`BlueButton`) instead of role (`Atom/Button/Primary`).
- Hard-coding hex/px in component fills/strokes/sizes — always reference variables.
- Reading `.pen` with the `Read` tool — encrypted, returns garbage.
- Writing reusables outside a single dedicated `Design System` frame.
- Skipping `placeholder: true` on slot children — downstream edits break.

## Reusable component checklist

```yaml
- name: "Atom/Button/Primary"
  reusable: true
  variants: [size: sm|md|lg, state: default|hover|active|disabled]
  fills: $color.action.primary.bg.{state}
  text:
    color: $color.action.primary.fg.{state}
    typography: $font.size.md / $font.weight.medium
  radius: $radius.md
  padding: { x: $space.4, y: $space.2 }
  placeholder: true   # for label slot
  source: { mode: pen-file, ref: "node:abc123" }
```

## Session pattern

```
1. open_document
2. get_editor_state(include_schema=true)              # once
3. get_variables                                       # baseline tokens
4. batch_get(ids=[...regions of interest...])
5. (analysis & decisions)
6. set_variables(...)                                  # tokens first
7. find_empty_space_on_canvas                          # placement
8. batch_design(... reusable: true ...)                # components
9. snapshot_layout(problemsOnly=true)                  # fix issues
10. search_all_unique_properties(property="fill")     # audit leaks
11. replace_all_matching_properties(...)              # bulk swap
12. get_screenshot per section                         # verification
```

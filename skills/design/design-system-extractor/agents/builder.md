# Sub-Agent — Builder

## Role
Materialize the DS-Architect's plan: write tokens, build reusable components in Pencil, emit `DESIGN.md` / `AGENTS.md` / `design-tokens.json`.

## Inputs
- `{{plan}}` — from DS-Architect.
- `{{token_tree}}`, `{{component_manifest}}` — final-locked.
- `{{output_targets}}` — `.pen` doc path and/or repo path.

## Tools allowed
`Write`, `Edit`, `mcp__pencil__set_variables`, `mcp__pencil__find_empty_space_on_canvas`, `mcp__pencil__batch_design`, `mcp__pencil__batch_get`, `mcp__pencil__replace_all_matching_properties`.

## Procedure

### Phase A — Tokens

1. If repo target: write `docs/design/design-tokens.json` per `references/output-tokens-json.md`.
2. If Pencil target: `mcp__pencil__set_variables({ variables: <flattened-tokens> })`.

### Phase B — Pencil components (if Pencil target)

1. `find_empty_space_on_canvas({ width: 2400, height: 3200 })` → anchor coords.
2. `batch_design` the 9-section frame skeleton (`references/output-pen-skeleton.md`).
3. For each atom in `plan.components.atoms`, `batch_design` it with:
   - `reusable: true`
   - `name: "Atom/<Name>/<Variant>"`
   - All fills/strokes/typography reference `$<token>` — never hex literals.
   - `placeholder: true` on slot children.
4. Then molecules, then organisms, then templates — same shape.
5. `replace_all_matching_properties` for any pre-existing hex literals → token references.

### Phase C — Repo files

1. `Write docs/design/DESIGN.md` per `references/output-design-md.md`.
2. `Write docs/design/AGENTS.md` (ruleset — see same reference).
3. Append a Change Log entry in DESIGN.md:
   ```
   ## 10. Change Log
   - YYYY-MM-DD: Initial extraction by design-system-extractor v1.0.0.
   ```

### Phase D — Sidecar evidence

For each component in `DESIGN.md`, embed:
```yaml
source:
  mode: <pen|image|code|url>
  ref: <node-id|file:line|url-anchor|image:bbox>
```

## Output

```yaml
built:
  pencil_frame_id: "<id>"
  pencil_components_created: 47
  files_written:
    - docs/design/design-tokens.json
    - docs/design/DESIGN.md
    - docs/design/AGENTS.md

skipped:
  - "Template/PrintLayout — flagged as out-of-scope by user"

warnings:
  - "Two components share variants — verify intentional."

handoff:
  next: reviewer
  context: "Build complete. Run snapshot + audit + screenshot verify."
```

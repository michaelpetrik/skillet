# Extraction Workflow — `.pen` Input

The user points at a `.pen` file (a Pencil design). Goal: produce tokens + reusable components in a new **Design System** frame inside the same document (or a sibling document if user prefers).

> Never call `Read` on a `.pen`. Use `mcp__pencil__*` exclusively.

## Step-by-step

### 1. Open & inventory

```
mcp__pencil__open_document({ path: "<path>.pen" })
mcp__pencil__get_editor_state({ include_schema: true })   # ONCE
mcp__pencil__get_variables({})                            # existing tokens
```

Cache:
- node count, frame count, page count
- existing variables (don't recreate)
- detected component names

If node count > 50 → escalate to multi-agent topology (see `orchestration.md`).

### 2. Region pass

For each top-level frame:

```
mcp__pencil__batch_get({ ids: [<frame_id>, <child_ids...>] })
mcp__pencil__get_screenshot({ nodeId: <frame_id>, scale: 1 })
```

Build a per-frame digest: list of unique fills, strokes, font sizes, spacing literals.

### 3. Token audit (Token-Auditor)

Aggregate raw values across frames → cluster:
- Cluster colors by hue/lightness similarity (≤ 5% delta) → single primitive.
- Cluster spacings by 4 pt grid → snap to nearest grid step.
- Cluster font sizes → minimum monotonic ramp covering observed sizes.

Output: token tree (`primitives → semantic → states`) per `tokens-taxonomy.md`.

### 4. Component audit (Component-Auditor)

For each repeated visual:
- ≥ 2 occurrences with identical structure → atom or molecule (decide by hierarchy rules).
- Variants are distinguished by 1 dimension (color or size). Multiple dimensions = separate variant axes.

Output: component manifest with hierarchy + variants + source node IDs.

### 5. Build

```
mcp__pencil__find_empty_space_on_canvas({ width: 2400, height: 3200 })
mcp__pencil__set_variables({ variables: <tokens> })       # tokens first
mcp__pencil__batch_design({
  parentId: <new_frame>,
  nodes: [
    { type: "frame", name: "Tokens", ... },
    { type: "component", name: "Atom/Button/Primary", reusable: true, ... },
    ...
  ]
})
```

Layout the new frame using the 9-section skeleton from `output-pen-skeleton.md`.

### 6. Verify

```
mcp__pencil__snapshot_layout({ frameId: <ds_frame>, problemsOnly: true })
mcp__pencil__search_all_unique_properties({ property: "fill" })
# anything not a $color.* reference → fix
mcp__pencil__get_screenshot({ nodeId: <each section>, scale: 1 })
```

Optional bulk fix:

```
mcp__pencil__replace_all_matching_properties({
  match: { fill: "#3B82F6" },
  set: { fill: "$color.brand.500" }
})
```

### 7. Emit sidecar artifacts

In the repo (or a workspace folder, ask user):
- `DESIGN.md` — `references/output-design-md.md`
- `design-tokens.json` — `references/output-tokens-json.md`
- `AGENTS.md` — short ruleset (no hex literals, atomic vocabulary, etc.)

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Variables returned `[]` | Doc has no tokens yet | Run `set_variables` after audit. |
| `batch_design` rejects unknown variable | Component refs token before it exists | Set tokens first, then design. |
| Many near-duplicate hex fills | Cluster threshold too tight | Loosen to 5–8% delta, re-cluster. |
| Components show as instances of ad-hoc nodes | `reusable: false` was used | Recreate with `reusable: true`. |

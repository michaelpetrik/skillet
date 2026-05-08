# Output Schema — Pencil **Design System** Frame Skeleton

When the build target is a `.pen` document, materialize a single dedicated **Design System** frame with **9 sections**, laid out as a 3 × 3 grid (or vertically stacked in narrow mode). This mirrors the proven `mT1L7-style` layout from prior projects.

## 9 sections

| # | Section | Contents |
|---|---|---|
| 1 | **Tokens — Color** | All 3 layers (primitives, semantic, state) as swatches with name + value labels. |
| 2 | **Tokens — Typography** | Type ramp specimen: H1..H6, body, caption, code. Show family, size, weight, line-height. |
| 3 | **Tokens — Spacing / Radius / Shadow / Motion** | Visual rulers + radius corners + shadow boxes + motion timings (static frame screenshots). |
| 4 | **Atoms** | Buttons, Inputs, Icons, Badges, Avatars, Labels, Dividers — each in all variants & states. |
| 5 | **Molecules** | Composed atoms: SearchBar, InputField, MenuItem, Toast, Card, Tag list. |
| 6 | **Organisms** | Header, Footer, Sidebar, ProductCard, DataTable, Form. |
| 7 | **Templates** | Page-level layouts: Marketing, Auth, Dashboard, Detail. Slot placeholders. |
| 8 | **Motion / Voice** | Motion principles (cards, callouts), voice samples (button labels, error messages). |
| 9 | **Do / Don't + Change Log** | Pattern table with green/red examples; appended change log entries. |

## Frame dimensions

- Default frame: **2400 × 3200**.
- Section grid: 3 columns × 3 rows, gutter `space.16` (64 px).
- Per-section title typography: `font.size.xl / weight.semibold`.
- Each section has a 1 px subtle border (`border.default`) and `padding: space.8`.

## Pencil node tree

```
Frame "Design System"  (reusable: false, but a singleton anchor)
├── Frame "1. Tokens — Color"
│   ├── ComponentInstance Atom/Swatch/Primitive  (×N)
│   ├── ComponentInstance Atom/Swatch/Semantic   (×N)
│   └── ComponentInstance Atom/Swatch/State      (×N)
├── Frame "2. Tokens — Typography"
│   └── ComponentInstance Atom/TypeSpecimen      (×N)
├── Frame "3. Tokens — Spacing/Radius/Shadow/Motion"
│   └── ComponentInstance Atom/<each>Specimen
├── Frame "4. Atoms"
│   └── ComponentInstance Atom/<each>            (every variant × every state)
├── Frame "5. Molecules"
│   └── ComponentInstance Molecule/<each>
├── Frame "6. Organisms"
│   └── ComponentInstance Organism/<each>
├── Frame "7. Templates"
│   └── ComponentInstance Template/<each>
├── Frame "8. Motion / Voice"
│   └── (notes + sample components)
└── Frame "9. Do / Don't + Change Log"
    └── (table of pattern examples)
```

## Rules

- The `Design System` frame itself is **not** reusable; it's the anchor.
- All children inside sections 4–7 MUST be **ComponentInstances** of `reusable: true` definitions placed elsewhere in the same doc (or imported from a library doc).
- Section order is fixed — agents that read this frame downstream rely on this order.
- Use `find_empty_space_on_canvas({ width: 2400, height: 3200 })` to place this frame; never overlap user artwork.

## Generation pseudocode

```ts
const ds = await pencil.batch_design({
  parentId: "<page>",
  position: await pencil.find_empty_space_on_canvas({ width: 2400, height: 3200 }),
  nodes: [{
    type: "frame",
    name: "Design System",
    layout: { mode: "grid", cols: 3, gap: 64, padding: 64 },
    children: [
      sectionFrame("1. Tokens — Color",   colorChildren),
      sectionFrame("2. Tokens — Typography", typeChildren),
      sectionFrame("3. Tokens — Spacing/Radius/Shadow/Motion", primChildren),
      sectionFrame("4. Atoms",            atomChildren),
      sectionFrame("5. Molecules",        moleculeChildren),
      sectionFrame("6. Organisms",        organismChildren),
      sectionFrame("7. Templates",        templateChildren),
      sectionFrame("8. Motion / Voice",   motionChildren),
      sectionFrame("9. Do / Don't + Change Log", patternChildren),
    ]
  }]
})
```

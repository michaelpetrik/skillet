# Token Taxonomy

Three layers. Always.

```
PRIMITIVES   →  SEMANTIC   →  STATES
(raw)         (intent)      (interaction)
```

- **Primitives** are the only place hex, px, ms, etc. literals live (`color.gray.700`, `space.4`, `radius.md`).
- **Semantic** tokens reference primitives and encode intent (`color.surface.default = color.gray.50`, `color.text.primary = color.gray.900`).
- **State** tokens reference semantic and encode interaction (`color.action.primary.bg.hover`).

Components consume **semantic + state** only. Never primitives directly.

## Token groups

### Color (3 layers each)

```
color.<scale>.<step>                primitive   color.gray.50..950, color.brand.50..950
color.<role>.<variant>              semantic    color.surface.default, color.text.muted
color.<role>.<variant>.<state>      state       color.action.primary.bg.hover
```

Required scales: `gray`, `brand`, `success`, `warning`, `danger`, `info`. Each scale has steps `50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950`.

Required semantic roles: `surface`, `surface.subtle`, `surface.elevated`, `border.default`, `border.strong`, `text.primary`, `text.secondary`, `text.muted`, `text.inverse`, `action.primary`, `action.secondary`, `action.danger`.

Required states per action role: `default`, `hover`, `active`, `focus`, `disabled`.

### Typography

| Token | Required values |
|---|---|
| `font.family.sans` / `serif` / `mono` | 1 each |
| `font.size.<step>` | `2xs, xs, sm, md, lg, xl, 2xl, 3xl, 4xl, 5xl` |
| `font.weight.<step>` | `regular, medium, semibold, bold` |
| `line.height.<step>` | `tight, snug, normal, relaxed, loose` |
| `letter.spacing.<step>` | `tight, normal, wide` |

### Spacing — 4 pt grid

`space.0..space.16` mapped as `0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 192`. Components must consume only these.

### Radius

`radius.none, radius.xs (2), radius.sm (4), radius.md (8), radius.lg (12), radius.xl (16), radius.2xl (24), radius.full (9999)`.

### Sizing

`size.icon.<sm|md|lg|xl>`, `size.control.<sm|md|lg>` (button/input height), `size.container.<sm|md|lg|xl>` (max-width).

### Shadow

`shadow.none, shadow.xs, shadow.sm, shadow.md, shadow.lg, shadow.xl, shadow.inner, shadow.focus`.

### Motion

`motion.duration.<instant(0)|fast(120)|base(200)|slow(320)|deliberate(500)>` (ms). `motion.ease.<linear|in|out|inOut|spring>`.

### Z-index

`z.base(0), z.dropdown(1000), z.sticky(1100), z.overlay(1200), z.modal(1300), z.popover(1400), z.toast(1500), z.tooltip(1600)`.

## Audit checklist

- [ ] Every primitive has a name; no raw hex/px outside primitives.
- [ ] Every semantic token references exactly one primitive.
- [ ] Every state token references exactly one semantic.
- [ ] Action roles have full state coverage (`default, hover, active, focus, disabled`).
- [ ] Type ramp is monotonic (size, line-height move together).
- [ ] Spacing values are all on the 4 pt grid.

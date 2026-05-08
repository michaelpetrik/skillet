# Output Schema — `DESIGN.md`

Agent-friendly semantic doc. The shape is fixed; sections may be empty but must exist in this order.

```markdown
# Design System — <Project Name>

> Source: <pen-file | url | code-repo | image-set>
> Generated: <YYYY-MM-DD>
> Version: <semver>

## 1. Principles

- 3-5 short, opinionated principles ("Calm contrast", "One emphasis per region", etc.).
- Tied to the brand voice. No generic platitudes.

## 2. Tokens

### 2.1 Colors
| Layer | Token | Value | Notes |
|---|---|---|---|
| primitive | color.brand.500 | #3B82F6 | base brand |
| semantic | color.action.primary.bg | $color.brand.500 | CTAs |
| state | color.action.primary.bg.hover | $color.brand.600 | -1 step |

### 2.2 Typography
| Token | Family | Size | Weight | Line | Letter |
|---|---|---|---|---|---|
| text.h1 | sans | 4xl | bold | tight | -0.02em |
| text.body | sans | md | regular | normal | 0 |

### 2.3 Spacing — 4 pt grid
List from `space.0` to `space.16`.

### 2.4 Radius / Shadow / Motion / Z-index
One table each.

## 3. Atoms
For each atom:
```yaml
- name: Atom/Button/Primary
  variants: [size: sm|md|lg, state: default|hover|active|focus|disabled]
  uses: [color.action.primary.*, font.size.md, radius.md, space.4]
  source: { mode: <mode>, ref: <id> }
  do: <one line>
  dont: <one line>
```

## 4. Molecules
Same shape, plus `composed_of: [atom-names]`.

## 5. Organisms
Same shape, plus `region: header|footer|sidebar|main` and `slots: [...]`.

## 6. Templates
Page-level scaffolding. List slots, breakpoints, responsive behavior.

## 7. Motion
Animation tokens + 3-5 motion principles ("respect prefers-reduced-motion", "use `motion.duration.fast` for hover", etc.).

## 8. Voice & Tone
Microcopy guidance: button labels, error messages, empty states, success messages.

## 9. Do / Don't
Top 10 patterns with one-line rationale each.

## 10. Change Log
Append-only log of token/component changes with date + reason.
```

## Companion: `AGENTS.md`

Short ruleset emitted alongside `DESIGN.md`:

```markdown
# AGENTS.md — Design System Rules

## Hard rules
- No raw hex/px in components. Reference `$color.*`, `$space.*`, `$radius.*` only.
- Components MUST follow atomic vocabulary (`Atom/`, `Molecule/`, `Organism/`, `Template/`).
- New visual decisions require a token first; no "one-off" colors.
- All interactive components MUST cover `default, hover, active, focus, disabled`.
- Respect `prefers-reduced-motion` in all motion-bearing components.

## Lint
- `bg-[#...]` Tailwind arbitraries → fail.
- Components missing `reusable: true` in Pencil → fail.
- Spacing values not on 4 pt grid → fail.
```

## File layout

```
docs/design/
├── DESIGN.md
├── AGENTS.md
├── design-tokens.json
└── snapshots/                # optional — per-section screenshots
```

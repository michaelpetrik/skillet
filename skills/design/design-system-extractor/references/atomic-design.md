# Atomic Design — Hierarchy & Naming

Brad Frost's atomic design adapted for this skill. The vocabulary is **strict**: never blur the boundary between an atom and a molecule.

## Hierarchy

| Level | What | Examples | Pencil reusable name |
|---|---|---|---|
| **Tokens** | Raw design decisions (no UI) | color, type, spacing, radius, shadow, motion | `Token/<group>/<name>` |
| **Atoms** | Smallest UI primitives, no children | Button, Input, Icon, Badge, Avatar, Label, Divider | `Atom/<Name>/<Variant>` |
| **Molecules** | Group of atoms working together | InputField (Label+Input+Help), SearchBar, MenuItem, Toast | `Molecule/<Name>/<Variant>` |
| **Organisms** | Composite UI regions | Header, Footer, Sidebar, ProductCard, DataTable, Form | `Organism/<Name>/<Variant>` |
| **Templates** | Page-level layouts (no real content) | DashboardLayout, AuthLayout, MarketingLayout | `Template/<Name>` |
| **Pages** | Templates with real data | (out of scope for the design system itself) | n/a |

## Naming rules

- **PascalCase** for the primary name.
- **Forward-slash variants**: `Atom/Button/Primary`, `Atom/Button/Ghost`, `Molecule/InputField/Error`.
- Density / size variants: append `--sm` / `--md` / `--lg` (`Atom/Button/Primary--sm`).
- States are **not** variants — they are token-driven (`hover`, `focus`, `disabled`, `loading`).

## Decomposition heuristics

**An atom must NOT contain another atom.** If you see two atoms together, that's a molecule.
**A molecule must NOT layout for a region.** If it does, it's an organism.
**An organism is replaceable as a unit.** If swapping it breaks the page contract, it's a template.

## Decision tree

```
Is it a single, indivisible UI primitive?      → Atom
Is it 2+ atoms forming one functional unit?     → Molecule
Is it a self-contained region of the screen?    → Organism
Does it define a page-level scaffolding?        → Template
```

## Anti-patterns

- "Card" containing only an icon and label → that's a **molecule**, not a card. Keep "Card" reserved for organism-level surfaces.
- "Button group" with 3 buttons → that's a **molecule** (`Molecule/ButtonGroup/Default`).
- "Section" used for a header → use **Organism** (`Organism/Header/Default`).
- One reusable per state → states are tokens; one component, multiple states.

## Source contract

Every atom/molecule/organism produced by this skill MUST cite its source:

```yaml
source:
  mode: pen-file | image | code-tailwind | url
  ref: <node-id | file:line | url-anchor | image:bbox>
  evidence: <hash or short quote>
```

This goes into `DESIGN.md` per component and into the per-component sidecar in the Pencil frame.

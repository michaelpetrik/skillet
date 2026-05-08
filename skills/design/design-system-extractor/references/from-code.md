# Extraction Workflow — Code Input

User points at a codebase containing a Tailwind config, CSS variables (`@theme`), a shadcn registry, or a CSS-in-JS theme. Goal: read the canonical numbers from code and project them into atomic tokens + components.

> Code is the easiest mode — values are exact. The work is **classification**, not **measurement**.

## Step-by-step

### 1. Locate the source of truth

Search for, in order:

```
Glob: tailwind.config.{js,ts,mjs,cjs}
Glob: **/styles/globals.css   (look for @theme)
Glob: components.json          (shadcn config)
Glob: **/tokens/*.{json,ts}
Glob: **/theme.{ts,js}         (CSS-in-JS)
```

If multiple exist, ask the user which is canonical (or treat the most-referenced one as primary).

### 2. Parse Tailwind config

```
Read tailwind.config.ts
```

Extract:
- `theme.extend.colors.*` → primitive color scales
- `theme.extend.fontFamily.*` → `font.family.*`
- `theme.extend.fontSize.*` → `font.size.*`
- `theme.extend.spacing.*` → `space.*`
- `theme.extend.borderRadius.*` → `radius.*`
- `theme.extend.boxShadow.*` → `shadow.*`
- `theme.extend.transitionDuration.*` → `motion.duration.*`
- `theme.extend.zIndex.*` → `z.*`

Tailwind v4 `@theme` is the preferred shape — it already gives you primitive tokens with names.

### 3. Parse CSS @theme / CSS variables

```
Grep: @theme
Grep: --[a-z]+-[0-9a-z]+:
```

CSS variables already resemble primitives. Map by prefix:
- `--color-*` → `color.*`
- `--text-*` → `font.size.*`
- `--spacing-*` → `space.*`
- `--radius-*` → `radius.*`

### 4. Parse shadcn registry

If `components.json` exists, the project consumes a shadcn registry. Use:

```
mcp__shadcn__get_project_registries
mcp__shadcn__list_items_in_registries
mcp__shadcn__view_items_in_registries({ items: [...] })
```

Each shadcn item gives you a canonical component (button, card, input, etc.) → use as atom/molecule reference.

### 5. Component scan

```
Glob: **/components/**/*.{tsx,jsx,vue,svelte}
Grep: className=
```

Cluster by component name → variants (via `cva`, `tailwind-variants`, or prop-driven className).

Each unique component → atom/molecule/organism (apply atomic-design hierarchy rules).

### 6. Build the semantic & state layers

Code typically gives you primitives only. Generate the missing layers:
- Semantic: read component classNames to infer roles (`bg-blue-500` → `color.action.primary.bg`).
- States: read variant maps (`hover:bg-blue-600` → `color.action.primary.bg.hover`).

### 7. Build artifacts

Emit (in this order):
1. `design-tokens.json` (W3C DTCG) — exact reflection of code values.
2. `DESIGN.md` — semantic narrative + atomic component list.
3. `AGENTS.md` — ruleset: "no Tailwind utility hex literals, only `@theme` references."
4. Optional: open a Pencil document and project tokens via `set_variables` to enable design-time work.

### 8. Verify against code

For each component listed in DESIGN.md, find at least one usage in the codebase (Grep on the component name) and confirm class-by-class that no token was missed.

## Common shapes

```ts
// Tailwind v4 @theme
@theme {
  --color-brand-500: #3B82F6;
  --space-4: 1rem;
  --radius-md: 0.5rem;
}
```

```ts
// tailwind.config.ts
export default {
  theme: { extend: { colors: { brand: { 500: "#3B82F6" } } } }
}
```

```ts
// CSS-in-JS
export const theme = {
  colors: { brand: { 500: "#3B82F6" } },
  space: { 4: "1rem" }
}
```

All three project to the same `color.brand.500 = #3B82F6` primitive.

## Pitfalls

- Tailwind defaults vs. `extend` — only `extend` is project-specific; defaults inflate token list.
- Arbitrary values (`bg-[#3B82F6]`) bypass the theme — treat as **leaks**, list in `AGENTS.md`'s lint section.
- Multiple sources of truth (Tailwind config + CSS vars + theme.ts) → reconcile before extraction.

---
name: design-system-extractor
description: Extract a structured design system (tokens, atoms, molecules, organisms following atomic design) from existing inputs — Pencil .pen files, screenshots, web URLs, HTML/CSS/Tailwind code, or design.md docs — and produce reusable artifacts (Pencil .pen skeleton with reusable components, DESIGN.md, design-tokens.json, AGENTS.md). Use when the user asks to "extract design tokens", "build a design system from this URL/image/.pen", "create design.md", "audit existing UI for atomic design", "systematize ad-hoc components", "vytvoř design system z…", or hands you a screenshot/.pen/URL/code and wants reusable components.
category: Design
version: 1.0.0
allowed-tools:
  - "mcp__pencil__*"
  - "Read"
  - "Write"
  - "Edit"
  - "Glob"
  - "Grep"
  - "Bash"
  - "WebFetch"
  - "WebSearch"
  - "Task"
metadata:
  author: Michael Petrik
  homepage: https://github.com/michaelpetrik/skillet
  tags: [design, design-system, atomic-design, pencil, design-tokens, extraction]
---

# Design System Extractor

Extract a coherent, atomic-design-aligned **design system** from any of these inputs:

| Input mode | Trigger |
|---|---|
| `pen-file` | User points at a `.pen` document (Pencil) |
| `image` | Screenshot, mockup PNG/JPG |
| `code-tailwind` | `tailwind.config.*`, `@theme` CSS, shadcn registry |
| `design-md` | Existing `DESIGN.md` / `design.md` |
| `url-storybook` | Live URL or Storybook |
| `figma-url` | Figma share link |
| `text-spec` | Free-form description |

The deliverable is always the same: **tokens → atoms → molecules → organisms** rebuilt as reusable components, plus machine-readable artifacts.

## When to Use

- "Extract design tokens from this Tailwind config / .pen / screenshot."
- "Build a design system from this URL."
- "Audit our existing UI and produce DESIGN.md + tokens.json."
- "Systematize the ad-hoc styles in this codebase."
- "Vytvoř design system z přiloženého .pen souboru."

## When to Skip

- One-off color picking from an image → use a color picker.
- Rebranding decisions (new palette, new type) → use `brand-storytelling` first.
- Generating new screens from a token doc → use `pencil-design` or `taste-design`.
- Net-new aesthetic exploration → use `taste-design`.

## Critical Rules

1. **Detect input first.** Always classify the input mode before any extraction. Wrong mode = wrong tools.
2. **Atomic hierarchy is non-negotiable.** Output MUST follow Tokens → Atoms → Molecules → Organisms → Templates. Never name a button group "card" or a card "section".
3. **Tokens before components.** Audit raw values FIRST (colors, spacing, type ramps). No component is built before its token primitives exist.
4. **Multi-analyst for large surfaces.** > 50 nodes / > 5 screens → spawn sub-agents (`Task` tool). Single-pass only for trivial inputs.
5. **Verify against source.** Every extracted token / component must be traceable to a source value. No invention without explicit user prompt.
6. **Never `Read` a `.pen` file.** They are encrypted. Use `mcp__pencil__*` exclusively.
7. **Reusable components only.** Every produced component MUST set `reusable: true` and live in a single `Design System` frame.

## Workflow

### Phase 1 — Discovery (read-only)

1. Detect input mode → load the matching reference:
   - `references/from-pen.md`
   - `references/from-image.md`
   - `references/from-code.md`
   - `references/from-url.md`
2. Load `references/tokens-taxonomy.md` and `references/atomic-design.md`.
3. For `.pen` input: `mcp__pencil__get_editor_state({ include_schema: true })` ONCE, then `batch_get` per region.
4. For URL/image: collect raw evidence (DOM snapshot, screenshot crops).
5. Inventory raw values: hex colors, font-family/size/weight, spacing literals, radii, shadows.

### Phase 2 — Synthesis

Decide topology (see table below). Then run the analysts in parallel via `Task`:

- **Token-Auditor** → cluster raw values → primitives + semantic + state layers.
- **Component-Auditor** → group repeated visuals → atoms/molecules/organisms.
- **Pattern-Detector** → spacing rhythm, type rhythm, motion patterns.
- **Visual-Analyst** *(image/url only)* → vision pass, pixel-measured rhythms.
- **Code-Parser** *(code only)* → AST/config parse of Tailwind, shadcn, CSS vars.

Consolidate into a single token & component manifest.

### Phase 3 — Build

1. **DS-Architect** drafts the target structure (frame layout in Pencil, file layout in repo).
2. **Builder** materializes:
   - In Pencil: `mcp__pencil__set_variables` first → then `batch_design` reusable components into a dedicated **Design System** frame (9 sections — see `references/output-pen-skeleton.md`).
   - In repo: write `DESIGN.md`, `design-tokens.json` (W3C DTCG), `AGENTS.md` ruleset.
3. **Reviewer** runs:
   - `mcp__pencil__snapshot_layout({ problemsOnly: true })` → fix layout issues.
   - `mcp__pencil__search_all_unique_properties` → assert no hex literals remain on top of tokens.
   - `mcp__pencil__get_screenshot` per section → visual diff vs. source.
   - `bash scripts/validate-skill.sh` (when targeting a skill repo).

## Tool Quick Reference

| Goal | Tool | Note |
|---|---|---|
| Read .pen state | `mcp__pencil__get_editor_state` | `include_schema: true` ONCE per session |
| Bulk inspect nodes | `mcp__pencil__batch_get` | reusable; preferred over many singletons |
| Set tokens | `mcp__pencil__set_variables` | run BEFORE creating components |
| Build component | `mcp__pencil__batch_design` | always `reusable: true` + naming `<Atom>/<Variant>` |
| Find empty canvas | `mcp__pencil__find_empty_space_on_canvas` | place new DS frame |
| Audit hex literals | `mcp__pencil__search_all_unique_properties` | catch token leaks |
| Bulk migrate values | `mcp__pencil__replace_all_matching_properties` | hex → token swap |
| Lint layout | `mcp__pencil__snapshot_layout` | `problemsOnly: true` |
| Visual verification | `mcp__pencil__get_screenshot` | per-section, not whole doc |
| Spawn analysts | `Task` | 6-8 agents on large surfaces |
| Parse code/config | `Read` + `Grep` | Tailwind, shadcn, @theme |
| Live page | `WebFetch` | DOM snapshot, never JS render |

## Common Mistakes

| Anti-pattern | Why it fails | Fix |
|---|---|---|
| Skip token audit, jump to components | Components encode hex literals → no theming | Run Token-Auditor first |
| Single-pass on 100+ nodes | Loses fidelity, hallucinates groupings | Spawn 3–6 sub-agents |
| Name group "card-like" | Breaks atomic vocabulary | Force atom/molecule/organism |
| `Read` the .pen | Encrypted file → garbage | Use `mcp__pencil__*` only |
| Components without `reusable: true` | Each instance disconnected | Always reusable + named variant |
| Hex literals after build | Token system bypassed | `search_all_unique_properties` audit gate |
| Editor state polled on every step | Token waste, slow | Once per session, cache result |

## Multi-Agent Topology

| Surface size | Topology | Agents |
|---|---|---|
| < 50 nodes / 1 screen | Single-pass | self |
| 50–500 nodes / 2–5 screens | 3-agent | Token-Auditor, Component-Auditor, Builder |
| 500+ nodes / mixed inputs | 6-agent | + Pattern-Detector, DS-Architect, Reviewer |
| Mixed sources (pen + url + code) | 8-agent multi-analyst-synthesis | + Visual-Analyst, Code-Parser |

Each analyst has a prompt template in `agents/`. See `references/orchestration.md` for the decision tree and dispatch templates.

## Outputs

| File | Schema | Reference |
|---|---|---|
| Pencil **Design System** frame | 9 sections (tokens, atoms, molecules, organisms, templates, motion, voice, do/don't, change log) | `references/output-pen-skeleton.md` |
| `DESIGN.md` | Semantic doc, agent-friendly | `references/output-design-md.md` |
| `design-tokens.json` | W3C Design Tokens Community Group format | `references/output-tokens-json.md` |
| `AGENTS.md` | Ruleset for downstream code/design agents | inline (see `output-design-md.md`) |

## Related Skills

- `pencil-design` — design new screens once a system exists.
- `taste-design` — premium visual standards layer (motion, asymmetry, typography rigor).
- `design-md` — alternate path: synthesize DESIGN.md from a Stitch project.
- `web-design-guidelines` — accessibility & UX review of the produced system.

## Resources

- [Atomic Design — Brad Frost](https://atomicdesign.bradfrost.com/)
- [W3C Design Tokens Community Group](https://www.w3.org/community/design-tokens/)
- [Material Design Tokens](https://m3.material.io/foundations/design-tokens/overview)
- [Tailwind v4 `@theme` directive](https://tailwindcss.com/docs/theme)

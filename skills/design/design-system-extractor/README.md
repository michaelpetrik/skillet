# Design System Extractor

Extract a structured design system (tokens, atoms, molecules, organisms following atomic design) from existing inputs — Pencil `.pen` files, screenshots, web URLs, HTML/CSS/Tailwind code, or `design.md` docs — and produce reusable artifacts.

## What you get

- A Pencil **Design System** frame with reusable components, organized in 9 sections.
- `DESIGN.md` — agent-friendly semantic design doc.
- `design-tokens.json` — W3C Design Tokens (DTCG) format.
- `AGENTS.md` — ruleset for downstream code/design agents.

## Install

With `npm`:
```bash
npx skills add michaelpetrik/skillet --skill design-system-extractor
```

With `bun`:
```bash
bunx skills add michaelpetrik/skillet --skill design-system-extractor
```

## Demo prompts

```
Extract a design system from /Users/me/Designs/landing.pen
```

```
Build a design system from this URL: https://linear.app — produce DESIGN.md and tokens.json.
```

```
Audit our Tailwind config and shadcn registry; group ad-hoc components into atoms/molecules.
```

```
Vytvoř design system z přiloženého screenshotu (atomic design hierarchie).
```

## How it works

1. **Detect input mode** — pen/image/code/url/figma/design-md/text-spec.
2. **Discovery** — load matching reference, inventory raw values.
3. **Synthesis** — spawn 3 / 6 / 8 sub-agents in parallel (Token-Auditor, Component-Auditor, Pattern-Detector, Visual-Analyst, Code-Parser, DS-Architect, Builder, Reviewer).
4. **Build** — set Pencil variables → batch-create reusable components → emit `DESIGN.md`, `design-tokens.json`, `AGENTS.md`.
5. **Verify** — layout snapshot, hex-literal audit, per-section screenshots.

## Layout

```
design-system-extractor/
├── SKILL.md
├── README.md
├── CHANGELOG.md
├── references/         # detailed how-to per input mode + outputs
├── agents/             # prompt templates for sub-agents
└── scripts/
    └── validate-skill.sh
```

## License

MIT © Michael Petrik

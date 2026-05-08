# Changelog

All notable changes to **design-system-extractor** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-08

### Added

- Initial release of `design-system-extractor`.
- Multi-mode input detection: `pen-file`, `image`, `code-tailwind`, `design-md`, `url-storybook`, `figma-url`, `text-spec`.
- Three-phase workflow: Discovery → Synthesis → Build.
- 8 sub-agent prompt templates: Token-Auditor, Component-Auditor, Pattern-Detector, Visual-Analyst, Code-Parser, DS-Architect, Builder, Reviewer.
- Multi-agent topology decision table (1 / 3 / 6 / 8 agents) keyed on surface size.
- Atomic design hierarchy enforcement (Tokens → Atoms → Molecules → Organisms → Templates).
- 3-layer token taxonomy (primitives → semantic → states) covering color, typography, spacing, radius, sizing, shadow, motion, z-index.
- Output schemas: Pencil 9-section Design System frame, `DESIGN.md`, `design-tokens.json` (W3C DTCG), `AGENTS.md`.
- Pencil MCP best-practices reference (top 10 patterns + anti-patterns).
- `scripts/validate-skill.sh` linter (frontmatter, name match, kebab-case, description length, broken markdown links).

### Notes

- `.pen` files are never read with `Read`; only `mcp__pencil__*` tools are used.
- Components produced are always `reusable: true`.

---
name: google-ai-studio-export-standardizer
description: Standardize Google AI Studio exported React/Vite apps that use non-standard client env injection, mismatched aliases, or AI Studio-specific config hacks. Use when Codex needs to normalize an exported AI Studio app to idiomatic Vite patterns, keep the change reversible, update docs/examples, and add regression checks that protect both standardization and rollback.
category: Coding
version: 1.0.0
---

# Google AI Studio Export Standardizer

Standardize Google AI Studio exported Vite apps without losing the ability to revert the export-specific behavior later.

## Workflow

1. Read repository instructions before editing anything.
2. Inspect `vite.config.*`, `tsconfig*.json`, `.env*`, README/onboarding docs, and client-side files that touch env vars or aliases.
3. Detect AI Studio export anti-patterns:
   - `loadEnv(...)` combined with `define: { 'process.env.*': ... }`
   - browser code reading `process.env.*` instead of `import.meta.env.*`
   - `@` alias pointing to project root instead of `src`
   - Vite and TypeScript aliases diverging
   - AI Studio-specific comments or HMR toggles mixed into otherwise standard Vite config
4. Add or update regression checks before implementation when the repo allows it.
5. Verify the red state if you added tests.
6. Apply the smallest normalization that keeps behavior intact.
7. Record a rollback path in the task notes or handoff.
8. Re-run the relevant test, typecheck, and build commands.

## Normalize

Apply these changes together unless local constraints require a subset:

1. Remove client env bridges from `vite.config.*`.
   - Delete `loadEnv(...)` if it only exists to feed browser-side `define`.
   - Delete `define` entries that inject `process.env.*` into the client bundle.
2. Keep only minimal Vite server behavior.
   - Preserve real local overrides such as disabling HMR, but express them with normal Vite config like `server: { hmr: false }`.
   - Do not preserve AI Studio scaffolding just because it came from the export.
3. Normalize aliases.
   - Point Vite `@` to `src`.
   - Align the active app TypeScript config (`tsconfig.app.json` or equivalent; use `tsconfig.json` only when that repo keeps app compiler options there) so `@/*` resolves to `./src/*`.
   - Add `baseUrl: "."` only if that repo's TypeScript tooling actually requires it for alias resolution.
4. Normalize browser env access.
   - Rewrite client code from `process.env.MY_KEY` to `import.meta.env.VITE_MY_KEY` only for values that are already intended to be public in the browser.
   - Preserve the original runtime contract when migrating env reads because `import.meta.env.*` values arrive as strings; add explicit parsing or comparisons when the old code expected booleans, numbers, or structured data.
   - Rename public env variables in `.env.example`, README, and setup docs to `VITE_*`.
5. Add the standard Vite env shim when needed.
   - Create `src/vite-env.d.ts` with `/// <reference types="vite/client" />` if client code now reads `import.meta.env`.

## Revert Mode

When the user asks to return to the AI Studio export behavior, reverse the same change set in a controlled order:

1. Restore previous client env reads.
2. Restore the previous Vite alias and matching TypeScript alias together.
3. Reintroduce any removed `define` bridge only if the original runtime contract explicitly depends on it.
4. Remove `src/vite-env.d.ts` only if nothing reads `import.meta.env`.
5. Restore `.env.example` and docs to the previous env names.
6. Re-run the same verification commands after reverting.

## Regression Coverage

Prefer low-cost regression checks that pin the normalized contract:

- `vite.config.*` no longer injects `process.env.*` into client code
- Vite alias `@` resolves to `src`
- TypeScript alias matches Vite alias
- client code reads `import.meta.env.VITE_*`
- docs/examples use the same public env names as the code

Use the repo's existing test stack when available. If none exists, a small Node file-reading test is acceptable for config-only normalization.

## Verification

Run the smallest useful set for the repo. Prefer:

1. focused regression tests
2. typecheck such as `npm run lint` or `tsc --noEmit`
3. production build such as `npm run build`

If a code intelligence tool covers the repo, use it for impact analysis first. If it does not cover config files well, note the fallback to local file inspection.

## Output Expectations

At the end, report:

1. which files were changed
2. which AI Studio anti-patterns were removed
3. what remains intentionally AI Studio-specific
4. the exact rollback sequence
5. which verification commands passed

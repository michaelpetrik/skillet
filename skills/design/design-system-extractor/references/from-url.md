# Extraction Workflow — Live URL Input

User points at a live URL (or Storybook). Goal: harvest tokens + atomic components from the rendered HTML/CSS.

> `WebFetch` returns markdown-converted text by default. For real DOM/CSS, treat the page as **HTML source + visual screenshot**.

## Limits

- No JavaScript execution. Single-page apps that render entirely client-side will yield empty markup.
- No interactivity → no hover/focus state capture.
- No font files / no real shadow specs unless inlined.
- Storybook is the **best** URL surface — it exposes one component per story with knobs visible.

If the page is SPA-only, **fall back to `from-image.md`** with a screenshot the user provides.

## Step-by-step

### 1. Fetch the page

```
WebFetch({
  url: "<page>",
  prompt: "Return the raw HTML, all <style> blocks, all <link rel=stylesheet href> URLs, computed colors of the most prominent regions, and font-family declarations."
})
```

Cache the response. If it returned only prose markdown (no CSS), retry with a more explicit prompt or fall back.

### 2. Pull stylesheets

For each linked stylesheet:

```
WebFetch({ url: "<css-url>", prompt: "Return raw CSS." })
```

Extract:
- `:root { --foo: ...; }` blocks → primitive tokens.
- `@media (prefers-color-scheme: dark)` → dark-mode token overrides.
- Class definitions for top-level components.

### 3. DOM region inventory

Parse the returned HTML for repeating component shells:
- `<header>`, `<nav>`, `<main>`, `<footer>` → organisms.
- `<button>`, `<input>`, `<a class="btn-*">` → atoms.
- `<form>`, `<article class="card">` → molecules / organisms.

Record class names — they are your component IDs.

### 4. Visual reconciliation

Ask the user to attach (or fetch via screenshot tool if available) a viewport screenshot of the URL. Then run `from-image.md` heuristics in parallel — visual evidence trumps stale CSS variables.

### 5. Storybook special-case

If the URL is `/storybook/iframe.html?id=...`:
- Each story is one component in isolation.
- `WebFetch` each story URL.
- Component name from the URL slug → atomic hierarchy mapping.
- Knobs / controls reveal the variant axes.

### 6. Token reconciliation

Merge:
- Primitives from CSS variables (highest authority).
- Components from DOM scan + class names.
- Spacings/radii from computed style hints.

### 7. Build & verify

Same downstream path as `from-pen.md` (`set_variables` → `batch_design` → `snapshot_layout` audit).

For verification, render each new component in Pencil and compare to the **screenshot** of the original (URL → image bridge); pure DOM vs. design comparison is unreliable without rendering.

## Pitfalls

- Sites with consent banners return banner CSS, not page CSS. Strip.
- Tailwind-built sites embed hex literals in `class=` attributes via JIT — there's no canonical token map; cluster the hex literals as in `from-image.md`.
- Fonts loaded via `@font-face` may be self-hosted with obscure family names — record the URL, treat as `font.family.<role>` semantic.
- Cookie walls / paywalls → the fetched HTML is the wall, not the product. Confirm with user before extracting.

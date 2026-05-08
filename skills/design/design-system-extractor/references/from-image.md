# Extraction Workflow — Image / Screenshot Input

User attaches a screenshot, mockup PNG/JPG, or photo of UI. Goal: extract tokens + atomic components by visual analysis.

> Vision pass + heuristics. No DOM, no canonical numbers — every value is an estimate that must be reconciled later.

## Step-by-step

### 1. Read the image

```
Read({ file_path: "<image>" })
```

Output: visual description, identified regions (header, hero, cards, footer, etc.).

### 2. Region tagging

Mark each region's bbox (rough %): header `[0-100, 0-8]`, hero `[0-100, 8-45]`, etc. Save this as a per-image inventory; the Visual-Analyst sub-agent uses it.

### 3. Color sampling

For each region, sample dominant colors:
- Background, foreground (text), accent (CTA), border.
- Cluster across regions with ≤ 5% delta → primitive scale (`color.brand.*`, `color.gray.*`).
- Map by role → semantic tokens.

Snap to nearest "round" hex (e.g., `#3B82F6` not `#3C81F7`) to keep the system tidy.

### 4. Type ramp inference

- Count distinct text sizes by visual hierarchy (h1 → small).
- Snap to a monotonic ramp: `2xs, xs, sm, md, lg, xl, 2xl, 3xl, 4xl, 5xl`.
- Detect weight by stroke thickness (regular vs. medium vs. semibold vs. bold).

### 5. Spacing rhythm

- Measure pixel gaps between sibling regions.
- Snap to 4 pt grid (`0, 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128`).
- If image scale is unknown, infer multiplier from a known element (button height ≈ 40 px = `space.10` baseline).

### 6. Radius / shadow / motion

- Radius: measure corner of a card/button. Snap to `xs, sm, md, lg, xl, 2xl`.
- Shadow: classify as `none | xs | sm | md | lg | xl` by blur extent.
- Motion: not inferable from a still image — leave default and flag for user.

### 7. Component proposal

Identify atoms / molecules / organisms from regions. State that all values are **inferred**, not measured.

### 8. Build

The same Pencil build path as `from-pen.md` (`set_variables` → `batch_design` reusables → screenshot verify).

If the user has no Pencil document open, prompt:
- "Create a new .pen file at <path>?" → then `open_document`.

### 9. Reconciliation pass

After build, render a side-by-side: original image vs. `get_screenshot` of new Design System frame.
List all values still uncertain:
- Inferred type sizes
- Inferred motion durations
- Inferred shadow specs
- Any color where source pixel didn't match a clean primitive

User confirms or corrects before final write.

## Heuristics

- **Single button height across image** → it's the canonical control height.
- **Text appears at exactly 3 sizes** → start with `sm, md, 2xl` and grow only on demand.
- **All shadows look the same** → one `shadow.md`, don't invent ramps.
- **Two greens at similar lightness** → cluster to one; don't ship duplicates.

## Limitations to disclose

- Pixel measurements assume image is at least 2x DPI; sub-1x screenshots distort spacing.
- Compression artifacts (JPEG) skew color sampling — prefer PNG.
- Hover/focus states cannot be inferred from a still image.

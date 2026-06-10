# Analyze Gradient & Shadow

Determine gradient direction, color stops, and shadow values for each widget in the header / body / footer sections.

## Inputs
- `source_image`: section PNGs (header / body / footer)
- `normalize_json`: per-root `normalize_design_code/widgets/*.json` — contains `fills.type`, `gradientStops`, `gradientTransform`, `effects`

## Steps

**1. Gradient Direction**
Read `fills.type == GRADIENT_LINEAR` and `gradientStops` from JSON.
Confirm direction visually from the screenshot:
- Top → Bottom: `begin: Alignment.topCenter, end: Alignment.bottomCenter`
- Left → Right: `begin: Alignment.centerLeft, end: Alignment.centerRight`
- Diagonal: measure angle from screenshot → map to nearest `Alignment` pair (e.g. `topLeft → bottomRight`)

Do **not** output the raw `gradientTransform` matrix.

**2. Gradient Colors**
Take hex values from `gradientStops[].color` in JSON (authoritative for stop values).
Cross-check with screenshot: stop 0 color must match the lighter/darker end of the visible blend.
If a stop has `opacity < 1` → use `Color(0xAArrggbb)` with the correct alpha byte.
If JSON has no gradient fill but PNG shows one → extract colors from PNG, mark `source: screenshot`.

**3. Shadow Detection**
JSON often omits shadow data. Scan the pixels **outside** the widget's bounding box in the screenshot:
- Dark alpha-blended band beyond the edge → `has_shadow: true`
  - `offset`: direction of the dark shift (positive Y = shadow below, positive X = shadow right)
  - `blur_radius`: width of the fade band in px (edge to fully transparent)
- No dark band → `has_shadow: false`

**4. Shape Validation**
Cross-check `cornerRadius` from JSON against the screenshot:
- `cornerRadius >= height / 2` → Pill → use `BorderRadius.circular(100)`
- Smaller value → `BorderRadius.circular(value)`
- Confirm internal padding visually matches the JSON `padding` field.

## Verification
- No shadow hallucination: pixels outside the edge matching the background color → `has_shadow: false`
- **Truth-source rule**: PNG determines *presence* (is there a gradient/shadow?); JSON determines *values* (stop colors, opacity, offset). If both present but colors differ → use JSON stops, flag `visual_mismatch` for review.
- Always output `Alignment` values — never raw angle degrees

## Output
Append the `# Decoration` section into the **same widget block** already written by `analyze_layout.md`:

```
widget: <name>
  # Layout        ← already written by analyze_layout.md
  ...
  # Decoration
  gradient:
    begin: Alignment.topLeft
    end: Alignment.bottomRight
    colors: [0xFF74EDD9, 0xFF228A78]
    stops: [0.0, 1.0]
  shadow:
    has_shadow: true
    offset: Offset(0, 4)
    blur: 12
    color: Color(0x1F000000)
```

Omit `gradient` block if the widget has no gradient fill.
Omit `shadow` block entirely if `has_shadow: false`.

# Analyze Layout

Determine the layout structure, shape, and sizing constraint of each widget in the header / body / footer sections.

## Inputs
- `source_image`: fullscreen PNG + section PNGs (header / body / footer)
- `normalize_json`: `normalize_design_code/figma_normalized.json` + per-root `normalize_design_code/widgets/*.json`

## Steps

**1. Shape Classification**
Inspect the bounding box in the screenshot:
- `Rectangle` — square corners or small `cornerRadius`
- `Pill/Capsule` — `cornerRadius >= height / 2` (fully rounded edges)
- `Perfect_Circle` — `width == height` with circular contour
- `Custom_Path` — freeform vector, irregular edges

**2. Anchor & Alignment**
Compare the widget's position to its parent container:
- Anchor: `Top` / `Bottom` / `Center` combined with `Left` / `Center` / `Right`
- Overlaps another widget → `Stack`
- Shared X-axis with siblings → `Column`; shared Y-axis → `Row`

**3. Spacing & Sizing**
Read `padding` and sibling `gap` from JSON. Classify width/height as:
- `fixed(Wpx × Hpx)` — explicit pixel value
- `expanded` — fills parent (match parent / Expanded)
- `wrap_content` — sized by children

Do **not** use absolute `screen_x / screen_y`. Use relative spacing only.

**4. Flutter Widget Mapping**
| Pattern | Flutter widget |
|---------|---------------|
| Vertical stack | `Column` |
| Horizontal stack | `Row` |
| Overlap | `Stack` |
| Scrollable | `ListView` / `SingleChildScrollView` |
| Card with radius | `Container(decoration: BoxDecoration(borderRadius: ...))` |
| Pill button | `ElevatedButton` + `StadiumBorder` |

## Verification
- `width ≠ height` → never classify as `Perfect_Circle`
- Output must **not** contain absolute coordinates — only alignment, flex direction, spacing
- Every widget must have: `shape`, `anchor`, `sizing`, `layout`, `flutter_widget`

## Output
Write one block per widget into `pre_plan.md`. Use the shared widget block format:

```
widget: <name>
  # Layout
  shape:          Pill | Rectangle | Circle | Custom
  anchor:         <vertical>-<horizontal>
  sizing:         fixed(Wpx × Hpx) | expanded | wrap_content
  padding:        EdgeInsets.symmetric(h:16, v:24)   ← from JSON padding; omit if zero
  gap:            12px                                ← from JSON itemSpacing; omit if none
  layout:         Column | Row | Stack
  flutter_widget: <widget>
```

The `# Decoration` section (gradient / shadow) is filled in by `analyze_gradient_shadow.md` for the same widget block.




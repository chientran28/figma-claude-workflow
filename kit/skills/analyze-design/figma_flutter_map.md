# Figma → Flutter Exotic Map
> Basic mappings → `figma_flutter_map_quick.md`
> Implementation code → `.ui-workspace/flutter_helper_design.md` (search the code in last column)

| Code | Figma construct | Flutter approach | Recipe |
|------|-----------------|------------------|--------|
| `FX-BOOL` | `BOOLEAN_OPERATION: SUBTRACT` | `ClipPath` + `CustomClipper<Path>` | FX-CLIP |
| `FX-MASK` | node type `MASK` | `Stack` + `ShaderMask` or `ClipPath` on sibling | FX-MASK |
| `FX-GLASS` | `BACKGROUND_BLUR` effect | `ClipRect` > `BackdropFilter(ImageFilter.blur)` > semi-transparent `Container` | FX-GLASS |
| `FX-IBLUR` | `LAYER_BLUR` effect | `ImageFiltered(imageFilter: ImageFilter.blur(...))` wrapping the node | — |
| `FX-ISHADOW` | `INNER_SHADOW` effect | no native — `inner_shadow_widget` pkg or negative `spreadRadius` approx | FX-NEU |
| `FX-MULTIFILL` | node has both image fill + gradient fill | `Stack`: `Image` first → gradient `Container` on top | FX-MULTIFILL |
| `FX-OPACITY` | fill-level `opacity` field (not node opacity) | bake into alpha: `Color(0xAArrrggbb)` — never wrap `Opacity` around gradient | FX-OPACITY |
| `FX-BLEND` | `blendMode: MULTIPLY/SCREEN/OVERLAY/…` | `ColorFiltered(colorFilter: ColorFilter.mode(color, BlendMode.xxx), child:...)` | — |
| `FX-RADGRAD` | `GRADIENT_RADIAL` fill | `RadialGradient(center:, radius:, colors:, stops:)` | — |
| `FX-ANGGRAD` | `GRADIENT_ANGULAR` fill | `SweepGradient(colors:, stops:)` | — |
| `FX-ISTROKE` | `strokeAlign: INSIDE` | Flutter border is always outside — use negative `margin` or `ClipRect` + oversized border | — |
| `FX-DASHSTROKE` | dashed / dotted stroke | `CustomPainter` with `Path` + `PathMetrics.extractPath(...)` | — |
| `FX-POLY` | `POLYGON` / `STAR` node | `CustomPaint` painter — or export as SVG if static | — |
| `FX-WRAP` | `layoutWrap: WRAP` | `Wrap(spacing:, runSpacing:, children:)` | — |
| `FX-SCALE` | `constraints: SCALE` horizontal/vertical | `FractionallySizedBox(widthFactor: w/parentW, heightFactor: h/parentH)` | — |
| `FX-ABSLAY` | absolute child inside an auto-layout frame | outer → `Stack`; auto-layout children in `Column/Row`; absolute child as `Positioned` | — |
| `FX-VARIANT` | `COMPONENT_SET` with variant properties | `StatelessWidget` + one enum param per variant axis (State, Size, Type…) | — |
| `FX-TAP` | `reactions[].trigger: ON_CLICK/ON_PRESS` | `GestureDetector(onTap:)` or `InkWell(onTap:)` + GoRouter navigate | — |
| `FX-CLIP` | custom organic / bezier shape (non-standard radius) | `ClipPath(clipper: CustomClipper<Path>)` — trace from Figma node bounds | FX-CLIP |
| `FX-GRADBDR` | gradient as border (outer container trick) | outer `Container(gradient)` + `padding: borderThickness` + inner `Container(solidBg)` | FX-GRADBDR |
| `FX-NEU` | neumorphic surface (dual shadow + gradient fill) | `BoxDecoration(gradient:, boxShadow: [lightHighlight, darkShadow])` | FX-NEU |
| `FX-TABBAR` | tab bar with protruding center FAB piece | `Stack`: back (frosted glass) + front (pill gradient) + FAB (neumorphic circle) | FX-TABBAR |
| `FX-SECTION` | `SECTION` node | structural wrapper only — map to `Column` or flatten/ignore | — |

---

## Gradient angle → Flutter Alignment

| Figma angle (°) | `begin` | `end` |
|-----------------|---------|-------|
| 0 (top→bottom) | `Alignment.topCenter` | `Alignment.bottomCenter` |
| 90 (left→right) | `Alignment.centerLeft` | `Alignment.centerRight` |
| 180 (bottom→top) | `Alignment.bottomCenter` | `Alignment.topCenter` |
| 270 (right→left) | `Alignment.centerRight` | `Alignment.centerLeft` |
| 45 (tl→br) | `Alignment.topLeft` | `Alignment.bottomRight` |
| 135 (tr→bl) | `Alignment.topRight` | `Alignment.bottomLeft` |
| arbitrary θ | `Alignment(cos(θ+π), sin(θ+π))` → `Alignment(cos(θ), sin(θ))` | — |

## Constraints → Flutter Sizing

| Figma constraint | Flutter |
|-----------------|---------|
| `LEFT` / `TOP` | fixed left/top — no special widget |
| `RIGHT` | `Align(alignment: Alignment.centerRight)` |
| `CENTER` | `Align(alignment: Alignment.center)` |
| `STRETCH` | `double.infinity` or `Expanded` |
| `SCALE` | `FractionallySizedBox(widthFactor: w/pw)` — see `FX-SCALE` |

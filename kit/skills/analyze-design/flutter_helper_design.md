# Flutter UI Design Helper

Implementation recipes for exotic Figma → Flutter patterns.
Each section is tagged with its `FX-xxx` code from `FIGMA_FLUTTER_MAP.md`.

> **Language rule:** All content in this file must be written in English.

---

## Core Rules (always apply)

**Dark mode** — never `Color(0xFF000000)` / `Colors.black` → use `Color(0xFF0A0A0A)` (pure black kills box shadows).

**Main screens** — always wrap body in `SingleChildScrollView` or `CustomScrollView`. Never `Column` as root body. {#ui-scroll-001}

**Thin borders 2026** — prefer `Border.all(color: Colors.white.withValues(alpha: 0.15), width: 1.0)` over heavy shadows to separate blocks.

**Shadow elevation** — high elevation: `blurRadius: 24, spreadRadius: 0, offset: Offset(0, 8), color: 0x29000000`. Low elevation: `blurRadius: 6, offset: Offset(0, 2), color: 0x66000000`.

---

## FX-GLASS — Glassmorphism (BackdropFilter) {#fx-glass}

> Trigger: `BACKGROUND_BLUR` effect on node, or frosted-glass visual in PNG.

```dart
ClipRRect(
  borderRadius: BorderRadius.circular(24),
  child: BackdropFilter(
    filter: ImageFilter.blur(sigmaX: 15, sigmaY: 15),
    child: Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        color: Colors.white.withValues(alpha: 0.07),
        border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
      ),
      child: child,
    ),
  ),
)
```

⚠ Always wrap `BackdropFilter` in `ClipRect` or `ClipRRect` — without it blur bleeds outside bounds.
⚠ Content behind the widget must be painted first in the tree.

---

## FX-GRADBDR — Gradient Border {#fx-gradbdr}

> Trigger: stroke is a gradient (not a solid color), or `gradientBorder` in normalized JSON.

Outer `Container` carries the gradient + `padding = borderWidth`. Inner `Container` has solid background.

```dart
Container(
  decoration: BoxDecoration(gradient: gradient, borderRadius: outerRadius),
  padding: EdgeInsets.all(borderWidth),
  child: Container(
    decoration: BoxDecoration(color: bgColor, borderRadius: innerRadius),
    child: content,
  ),
)
```

---

## FX-MULTIFILL — Image + Gradient Overlay {#fx-multifill}

> Trigger: `deco._requiresGradientOverlayStack == true`, or node has both IMAGE and GRADIENT fill.

Never put both in `BoxDecoration` (wrong render order). Use `Stack`:

```dart
ClipRRect(
  borderRadius: BorderRadius.circular(radius),
  child: Stack(children: [
    Image.asset(path, fit: BoxFit.cover, width: double.infinity, height: double.infinity),
    Positioned.fill(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter, end: Alignment.bottomCenter,
            colors: [Colors.transparent, Color(0xCC000000)],
          ),
        ),
      ),
    ),
  ]),
)
```

---

## FX-OPACITY — Gradient Opacity Baked {#fx-opacity}

> Trigger: fill has `opacity` field, or node-level opacity on a gradient container.

Never wrap a gradient `Container` in `Opacity()`. Bake opacity into each stop's alpha:

```
30% opacity → AA = hex(0.30 × 255) = 0x4D
#111111 at 30% → Color(0x4D111111)
```

When `_gradientOpacityBaked: true` in normalized JSON → colors already baked, use directly.

---

## FX-NEU / FX-ISHADOW — Neumorphism & Inner Shadow {#fx-neu}

> Trigger: `INNER_SHADOW` effect, or neumorphic surface (dual contrasting shadows + gradient fill).

Flutter has no native `inset` shadow. Options:

- **Package (recommended):** `inner_shadow_widget: ^2.1.0`
- **Approximation:** negative `spreadRadius` on `BoxShadow`
- **TODO comment:** when exact rendering not critical

Neumorphic surface pattern (dual shadow + gradient):
```dart
BoxDecoration(
  gradient: LinearGradient(colors: [Color(0xFFF5F5F9), Color(0xFFDADFE7)]),
  shape: BoxShape.circle, // or borderRadius
  boxShadow: [
    BoxShadow(color: Color(0x80FFFFFF), blurRadius: 20, offset: Offset(-10, -10)), // light
    BoxShadow(color: Color(0x800D1431), blurRadius: 20, offset: Offset(10, 10)),   // dark
  ],
)
```

---

## FX-CLIP — Custom ClipPath / Organic Shape {#fx-clip}

> Trigger: `BOOLEAN_OPERATION: SUBTRACT`, custom bezier edges, diagonal cuts, parallelogram, non-standard clip.

General pattern:
```dart
ClipPath(clipper: _MyClipper(), child: ...)

class _MyClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    // trace path from Figma node bounds
    return Path()..moveTo(...)...close();
  }
  @override bool shouldReclip(_) => false;
}
```

**If ClipPath clips inner content (icons, text):** use `CustomPaint` for background shape instead — content is NOT clipped. See `UI-LAYOUT-008`.

---

## FX-MASK — Mask Node {#fx-mask}

> Trigger: Figma layer marked as `MASK` (mask icon in layers panel).

Approach: the MASK node defines the visible area for siblings above it in the same GROUP.

```dart
// Option A — ShaderMask (for image masks)
ShaderMask(
  shaderCallback: (bounds) => LinearGradient(...).createShader(bounds),
  blendMode: BlendMode.dstIn,
  child: contentWidget,
)

// Option B — ClipPath (for shape masks)
ClipPath(clipper: _ShapeFromMaskClipper(), child: contentWidget)
```

---

## FX-TABBAR — Complex Tab Bar with Protruding FAB {#fx-tabbar}

> Trigger: tab bar has distinct center piece protruding above the bar, and/or neumorphic center button.
> In Figma: a "Subtract" boolean shape over a frosted glass back layer.

Structure:
```
SizedBox(height: 100)
└── Stack
    ├── [Back]   Positioned(bottom:0) — full-width frosted glass bar (88px)
    │            ClipRect > BackdropFilter(blur 25) > Container(gradient + border)
    │            └── Row(spaceBetween): left_icon │ reserved space │ right_icon
    │
    └── [Front]  Positioned(left: sw*0.169, right: sw*0.169, top:0, bottom:0)
                 Container(gradient + border + shadow, borderRadius: 50)
                 └── Positioned(center top:12) → neumorphic FAB (see FX-NEU)
```

Back layer:
```dart
Positioned(
  left: 0, right: 0, bottom: 0,
  child: ClipRect(
    child: BackdropFilter(
      filter: ImageFilter.blur(sigmaX: 25, sigmaY: 25),
      child: Container(
        height: 88,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [Color(0x423A3A6A), Color(0x4225244C)]),
          border: Border.all(color: Color(0x807582F4), width: 0.5),
        ),
        padding: const EdgeInsets.fromLTRB(32, 0, 32, 24),
        child: Align(
          alignment: Alignment.bottomCenter,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              leftIcon,
              SizedBox(width: 107 + 44), // reserve space for FAB
              rightIcon,
            ],
          ),
        ),
      ),
    ),
  ),
)
```

Front pill — always use `MediaQuery` width, never hardcode Figma px:
```dart
Positioned(
  left: MediaQuery.of(context).size.width * 0.1692,
  right: MediaQuery.of(context).size.width * 0.1692,
  top: 0, bottom: 0,
  child: Container(
    decoration: BoxDecoration(
      gradient: LinearGradient(begin: Alignment.bottomCenter, end: Alignment.topCenter,
        colors: [Color(0xFF262C51), Color(0xFF3E3F74)]),
      borderRadius: BorderRadius.circular(50),
      border: Border.all(color: Color(0x807582F4), width: 0.5),
      boxShadow: [BoxShadow(color: Color(0xFF7582F4), blurRadius: 4, offset: Offset(0, 4))],
    ),
    child: Stack(children: [
      Positioned(left: 0, right: 0, top: 12, child: Center(child: NeuFabButton())),
    ]),
  ),
)
```

Gotchas:
- `BackdropFilter` without `ClipRect` → blur bleeds outside bounds ❌
- `Opacity` on `BackdropFilter` → breaks rendering ❌
- Hardcode `left: 65.9` from Figma px → breaks on other screen sizes ❌

---

## Error Patterns

### UI-LAYOUT-005 — Parallelogram direction reversed {#ui-layout-005}
> Symptom: left side is higher but design requires right side higher.

Fix — swap which corner starts at `y=0`:
```dart
// ✅ right higher: left starts at y=skew, right starts at y=0
..moveTo(0, s + r)  ..lineTo(w - r, 0)
// ❌ left higher: left starts at y=0, right starts at y=skew
..moveTo(0, r)      ..lineTo(w - r, s)
```

---

### UI-LAYOUT-006 — Filter items not filling full width {#ui-layout-006}
> Symptom: `SingleChildScrollView` + fixed-width items → only left side occupied.

Fix — `Row` + `Expanded` per item, remove fixed width:
```dart
Row(children: [
  for (int i = 0; i < items.length; i++) ...[
    Expanded(child: ItemWidget(...)),
    if (i < items.length - 1) const SizedBox(width: 10),
  ],
])
```

---

### UI-LAYOUT-007 — Hero banner with diagonal bottom cut {#ui-layout-007}
> Symptom: `BoxDecoration(borderRadius: ...)` rounds equally — can't make diagonal edge.

Fix — `ClipPath` with `CustomClipper` tracing the diagonal:
```dart
ClipPath(
  clipper: const _DiagonalClipper(notch: 10.0, radius: 20.0),
  child: Container(height: 240, decoration: BoxDecoration(gradient: ...)),
)
```

---

### UI-LAYOUT-008 — ClipPath clips inner icon {#ui-layout-008}
> Symptom: parallelogram/custom shape clips the icon at skewed corners.

Fix — use `CustomPaint` for background only; icon is in `Stack` above (never inside ClipPath):
```dart
Stack(children: [
  if (isSelected) Positioned.fill(child: CustomPaint(painter: _ShapePainter())),
  Center(child: Icon(...)), // outside ClipPath — never clipped
])
```

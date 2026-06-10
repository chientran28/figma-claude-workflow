# UI Failed — Error Registry

Each row is a UI bug that has been encountered and has a standard fix.
Agents read this file to self-correct without asking the user again.

> **How to use:** Match the `Root cause` column against the pattern you are encountering.
> For the detailed fix, see the `Ref` column → open the corresponding anchor in `flutter_helper_design.md`.
> Anchors are stable across section renumbering — the `knowledge-eval.sh` hook flags any dead link.

---

| Error code | Bug name | Root cause | Ref |
|---|---|---|---|
| UI-GRADIENT-001 | Gradient too dark / faded | `Opacity()` wrapping a `Container` with `BoxDecoration.gradient` → double-apply opacity | `flutter_helper_design.md#ui-gradient-001` |
| UI-GRADIENT-002 | Gradient hidden by image | `BoxDecoration` uses both `image` and `gradient` → Flutter renders gradient under the image | `flutter_helper_design.md#ui-gradient-002` |
| UI-SHADOW-001 | Inner shadow not visible | `BoxShadow` has no `inset` property in Flutter | `flutter_helper_design.md#ui-shadow-001` |
| UI-LAYOUT-001 | Glassmorphism not blurring background | Missing `ClipRRect` wrapping `BackdropFilter` | `flutter_helper_design.md#ui-layout-001` |
| UI-LAYOUT-002 | Gradient border appears as solid square | Using a plain `Border` instead of the nested Container pattern | `flutter_helper_design.md#ui-layout-002` |
| UI-SCROLL-001 | Main screen overflows vertically | `Column` directly in `Scaffold.body` without `SingleChildScrollView` | `flutter_helper_design.md#ui-scroll-001` |
| UI-OVERFLOW-001 | Text overflows in Row | `Text` inside `Row` not wrapped in `Expanded` | `coding-ui SKILL.md — Code Rules` |
| UI-COLOR-001 | Shadow invisible on dark background | Using `Colors.black` / `Color(0xFF000000)` as background → shadow cancelled | `flutter_helper_design.md#ui-color-001` |
| UI-COLOR-002 | Inline hex for semi-transparent overlay instead of palette expression | `Color(0x33FFFFFF)` hardcoded when token_palette specifies `Colors.white.withValues(alpha:0.20)` — use the palette expression, never bake raw ARGB hex for alpha overlays | `flutter_helper_design.md#ui-color-002` |
| UI-LAYOUT-003 | Category filter items at same height, no staircase | `ListView` doesn't support per-item vertical offset by index | `flutter_helper_design.md#ui-layout-006` |
| UI-LAYOUT-004 | Product card is a plain rectangle instead of parallelogram | `BoxDecoration.borderRadius` cannot create a parallelogram; need `ClipPath` + custom clipper | `flutter_helper_design.md#ui-layout-005` |
| UI-LAYOUT-005 | Parallelogram direction reversed (left higher instead of right) | Clipper path draws top-left at y=0 and top-right at y=skew → invert: top-left y=skew, top-right y=0 | `flutter_helper_design.md#ui-layout-005` |
| UI-LAYOUT-006 | Category filter items don't fill full screen width | `SingleChildScrollView` + fixed-width items → use Row + Expanded + remove fixed width | `flutter_helper_design.md#ui-layout-006` |
| UI-LAYOUT-007 | Hero banner has flat bottom instead of diagonal cutout | `BorderRadius.circular` rounds all 4 corners equally → use `ClipPath` with a diagonal bottom path | `flutter_helper_design.md#ui-layout-007` |
| UI-LAYOUT-008 | NavItem parallelogram clips the icon | `ClipPath` around the icon → icon cut at the parallelogram corners; use `CustomPaint` for the background instead | `flutter_helper_design.md#ui-layout-008` |

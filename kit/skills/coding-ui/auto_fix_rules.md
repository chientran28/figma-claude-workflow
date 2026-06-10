# auto_fix_rules — Pre-flight Auto-fix & Mandatory Rendering Rules

Read at **Step 0 (Pre-flight)**. Apply silently before writing any widget.
This is the **static baseline**. Project-learned fixes in `.ui-workspace/flutter_helper_design.md`
(and the matching `ui_failed.md` codes, auto-injected by the known-patterns hook) are richer
and **take precedence** when they cover the same root cause — don't duplicate them here.

---

## Pre-flight reads

```bash
cat .ui-workspace/ui_failed.md 2>/dev/null              # learned error codes (hook also injects these)
cat .ui-workspace/flutter_helper_design.md 2>/dev/null  # learned correct-fix patterns (authoritative)
cat .claude/skills/analyze-design/figma_flutter_map_quick.md 2>/dev/null  # Figma type → Flutter widget
```

---

## Auto-fix silently  (baseline — a learned `flutter_helper_design.md` pattern overrides any row)

| Pattern | Fix |
|---------|-----|
| `gradient` + `opacity < 1.0` | Bake alpha into stop colors |
| `_requiresGradientOverlayStack` | Stack: image → `Positioned.fill` gradient |
| `boxShadow[].isInner == true` | `inner_shadow_widget` |
| `backdropFilter` | `ClipRRect > BackdropFilter > Container` |
| Screen root no scroll | Wrap with `SingleChildScrollView` |
| `Text` in `Row` no `Expanded` | Add `Expanded` |
| Fill `#000000` / `Colors.black` | Use `Color(0xFF121212)` |

---

## Mandatory rendering rules (before coding)

- `RULE-ICON-001`: VECTOR/icon → check `assets.md` before `Icons.*`
- `RULE-BG-001`: background image → `Positioned.fill`, never fixed pixel sizes
- `RULE-SHAPE-001`: complex shape → `CustomPainter`/`ClipPath` (pause: A/B/C if present)

Read `figma_normalized.json`. Use QUICK map by default; full map only for exotic types (POLYGON, STAR).

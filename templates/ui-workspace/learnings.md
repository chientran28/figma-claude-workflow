# learn-from-failed — Skill Meta-Learnings

This file stores insights about **HOW** the `learn-from-failed` skill should run better.

- `flutter_helper_design.md` → bug patterns (WHAT the fix is)
- `ui_failed.md` → error registry (code → reference mapping)
- **This file** → process knowledge (HOW the skill classifies and handles bugs)

Agents must **read this file at Step 0** before executing `learn-from-failed`.

---

## Common Misclassifications to Watch For

- "Widget not showing" → often **LAYOUT** (z-index / Stack ordering), not ASSET
- "Color looks wrong in dark mode" → often **COLOR** — check if `Color(0xFF000000)` pure black used
- "Gradient not visible" → check **UI-GRADIENT-001** first (Opacity wrapper double-applying alpha)
- "Shadow missing" → check **UI-SHADOW-001** (inner shadow Flutter limitation) OR **UI-COLOR-001** (dark bg cancels shadow)
- "Animation jank" → check if `RepaintBoundary` is missing (not ANIM category, it's a LAYOUT concern)
- "Image blurry / wrong size" → check `BoxFit` and `Image.asset` scale parameter before calling it ASSET

---

## User Description → Category Hints

| User says (VN / EN) | Likely category | Check first |
|---|---|---|
| "bị cắt", "clipped", "không thấy full" | OVERFLOW or LAYOUT | Is it inside a `Row`/`Column` without `Expanded`? |
| "không cuộn được", "tràn màn hình" | SCROLL | Is body a `Column` without `SingleChildScrollView`? |
| "màu sai", "dark mode vỡ" | COLOR | Is `Colors.black` / `Color(0xFF000000)` used? |
| "chữ bị tràn", "text overflow" | OVERFLOW | Is `Text` inside `Row` without `Expanded`? |
| "gradient tối quá / nhạt quá" | GRADIENT | Is `Opacity()` wrapping the gradient container? |
| "bóng đổ không hiện", "shadow missing" | SHADOW or COLOR | Is background dark? Is `inset` shadow being simulated? |
| "animation giật", "không chạy" | ANIM | Check `controller.dispose()` and `RepaintBoundary` |
| "ảnh không load", "image broken" | ASSET | Check asset path in `pubspec.yaml` and `BoxFit` |
| "parallelogram", "diagonal", "cắt góc" | LAYOUT | Use `ClipPath` + custom clipper, not `borderRadius` |
| "glassmorphism", "blur background" | LAYOUT | Missing `ClipRRect` wrapping `BackdropFilter` |

---

## Process Insights

Insights are appended here after **every** `learn-from-failed` cycle (Step 8 is now mandatory).

**Entry format (one line each):**
```
[CATEGORY] YYYY-MM-DD: <takeaway>
```

`CATEGORY` ∈ `MISCLASSIFY` | `PATTERN_HINT` | `PROCESS` | `KNOWLEDGE_GAP`

**Retention rule:** entries older than **30 days** are automatically moved to
`learnings_archive.md` by the `knowledge-eval.sh` hook on every write to this
file. Keep this file as the active working set; never let it exceed ~60 entries.

<!-- Example:
[MISCLASSIFY] 2026-05-15: "Background blur not working" always means missing ClipRRect → map to UI-LAYOUT-001 without asking further.
-->


# get-exist-design — Project Design Scanner

Scans the Flutter project to collect existing **widgets** and **assets**, then writes the
results to `.ui-workspace/exist_design/widgets.md` + `assets.md` (overwrites if present).
Colors and fonts are NOT registered here — `make-ui-plan` validates them by grepping the real
Dart files listed in `figma_config.json → project_sources` (ground truth), so a registry would
only drift. This is a **command**, not part of the automated pipeline.

## When to run
- **Once at setup** — `/init-ui-workspace` Phase 3c calls it after discovering `project_sources`.
- **Before `/organize-figma`** when `.ui-workspace/exist_design/` is missing or stale.
- `organize-figma` STOPs and asks you to run it when `exist_design/*.md` is missing/empty — it
  never auto-runs this (a full project scan is heavy). Re-run it after you add shared widgets/assets.

---

## Step 1 — Locate Source Files

Run 2 scan groups in parallel:


**Widgets:**
```bash
find lib/widgets/ lib/shared/widgets/ lib/core/widgets/ -name "*.dart" 2>/dev/null
find lib/pages/ lib/features/ -type d -name "widgets" 2>/dev/null
find lib/pages/ lib/features/ -name "*.dart" | head -20
```

**Assets:**
```bash
find assets/ -type f | sort 2>/dev/null
grep -A 30 "assets:" pubspec.yaml
```

**If a key file is not found** → ask the user before continuing:
```
I couldn't find the [colors / widgets / fonts / assets] definition file.
Where is it stored? Send the path, or skip if it doesn't exist yet.
```

---

## Step 2 — Extract & Classify

### widgets.md

1. Read the first 15 lines of each widget file to capture `class <Name> extends Stateless/StatefulWidget`.
2. Classify:
   - **Public**: `lib/widgets/`, `lib/shared/widgets/`, `lib/core/widgets/`
   - **Private**: `widgets/` sub-folders inside pages/features
   - **Pages**: files named `*_page.dart`, `*_screen.dart`
3. For each widget write: short code base on `token-naming-rules.md`, class name, file path, one-line description.

### assets.md

1. List files by directory.
2. Classify: Images (`jpg`, `png`) / Icons (`SVG` in icons/) / SVG.
3. Write the pubspec.yaml declared paths at the top of the file.
3. For each assets write: short code base on `token-naming-rules.md`, class name, file path, one-line description.
---
## Step 3 Read Naming Rules
Read **before writing to `exist_design/*.md` registry:**
```bash
cat .claude/rules/token-naming-rules.md
```
## Step 4 — Write Files

Write to `.ui-workspace/exist_design/` (the canonical location every other skill reads):

| File | Format |
|---|---|
| `widgets.md` | Source paths → Public table → Private table → Pages table |
| `assets.md` | pubspec paths → Images → Icons → SVG → folder tree |

Each constant/widget/asset gets a **short code** like `[PREFIX-N]` for quick lookup.
Write the source file path at the top of each output file.

---

## Step 5 — Summary

```
exist_design/ updated:
  widgets.md    — P public, Q private, R pages
  assets.md     — T images, U icons, V SVG
```

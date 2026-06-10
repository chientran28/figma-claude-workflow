# Pipeline Architecture

## Why isolated subagents?

Each step runs in a separate subagent spawned by `organize-figma`. This keeps the main coordinator context lean — Figma MCP responses (large JSON payloads) and PNG screenshots never accumulate in the main context, so no manual `/compact` is needed across a full pipeline run.

## Step breakdown

### Step 1 — Normalize (`figma-extract-agent`)

**Trigger:** `organize-figma` spawns this agent with the Figma node URL.

**What it does:**
1. Calls `get_design_context` → raw layout JSON (`figma_layout.json`)
2. Calls `get_styles` / `export_tokens` → design tokens (`figma_design_tokens.json`)
3. Calls `save_screenshots` (fullscreen @ 2x, per-root-widget @ 3x)
4. Runs `figma_preprocessor.py` (7 passes) → `figma_normalized.json` + per-widget JSON files

**Key file:** `commands/scripts/figma_preprocessor.py`

Preprocessor passes:
- Pass 1: Token resolution — Figma variable refs + hex → Dart constants (reads `token_map.json`)
- Pass 2: Frame flattening — remove pass-through single-child wrappers
- Pass 3: Decoration + layout — fills, gradients, borders, shadows, Auto Layout → Row/Column, Stack + Positioned
- Pass 3.5: Text normalization — TEXT → `Text()` + `TextStyle`
- Pass 4: Instance resolution — Figma components → Flutter widget hints
- Pass 5: Sizing constraints — px bounds → `flutterWidth`/`flutterHeight`, FILL → `Expanded`
- Pass 6: Screen layout map — z-order, screen-relative positions, role classification
- Pass 7: Per-widget export — one JSON + one PNG per root widget

**Output:**
```
.ui-workspace/<feature>/
├── figma_code/figma_layout.json
├── figma_code/figma_design_tokens.json
├── figma_fullscreen/<feature>_fullscreen.png
├── figma_widget/<id>_<name>.png  (one per root)
└── normalize_design_code/
    ├── figma_normalized.json
    └── widgets/
        ├── _manifest.json
        └── <id>_<name>.json  (one per root)
```

---

### Step 2 — Analyze (`analyze-design-agent`)

**Trigger:** `organize-figma` spawns this agent after normalization.

**What it does:**
1. Reads `figma_normalized.json` + fullscreen PNG + per-widget PNGs
2. Classifies each root widget: `SIMPLE` (stateless, no business logic) vs `COMPLEX` (needs notifier)
3. Maps decoration: fills → `dartConst`, gradients → `LinearGradient`, shadows → `BoxShadow`
4. Determines screen type (Main/Push/BottomSheet/Dialog), scaffold conventions
5. Identifies state enum variants
6. If `enable_html_visualization: true` — generates `preview.html` (iPhone 17 mockup)
7. Writes `plan/pre_plan.md`

**Output:** `plan/pre_plan.md` (+ `preview.html` if visualization enabled)

---

### Step 3 — Plan (`ui-plan-architect`)

**Trigger:** `organize-figma` spawns this agent after user confirms pre_plan.md.

**What it does:**
1. Reads `pre_plan.md` + `figma_config.json` + `exist_design/widgets.md` + `exist_design/assets.md`
2. Resolves each design token: NEW (add to AppColors/AppSVGs) vs REUSE (existing constant)
3. Studies sibling screens for code style (HookConsumerWidget patterns, AppBar style, etc.)
4. Defines widget phases with coding order, file paths, state enum
5. Writes `plan/plan.md` with `## New Token Definitions` table + `## Widget Phases` table

**Output:** `plan/plan.md`

---

### Step 4 — Code (`ui-code-agent`)

**Trigger:** `organize-figma` spawns this agent once per widget phase row.

**What it does:**
1. Reads `plan.md` + widget PNG + `figma_normalized.json`
2. Writes Dart files following project code style (Riverpod, Freezed, GoRouter)
3. Runs `flutter analyze` and fixes all lints before reporting done
4. Updates `widgets.md` and `assets.md` status

**Output:** Dart files in `lib/features/<feature>/`

---

## Knowledge accumulation

The pipeline learns over time via `/learn-from-failed`:
- `flutter_helper_design.md` — rendering patterns (gradient tricks, overflow fixes, shadow approaches)
- `ui_failed.md` — error codes + root causes + fixes
- `learnings.md` — meta-learnings (misclassification patterns, widget hints)

The `known-patterns-inject.sh` hook injects relevant patterns from `learnings.md` into every Claude Code prompt automatically.

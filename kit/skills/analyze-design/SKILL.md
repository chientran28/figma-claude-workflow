---
name: analyze-design
description: >
  Analyze visual design from Figma screenshots and normalized JSON. Classifies every root
  (layout, decoration, behavior), maps design-token colors, determines screen states, and
  produces a structured Pre-Plan for the Flutter code phase.
allowed-tools: Read, Write, Edit, Glob, Grep
version: 3.2.0
---

Every mobile screen has three zones: **Header** (top — title/nav), **Body** (middle — content),
**Footer** (bottom — actions/nav). Analyze layout + shape of all three. Inspect — do not guess.

**Source-of-truth rule:** **widget PNG > JSON.** Use JSON for precise values (stops, padding,
cornerRadius); use the PNG to confirm presence and catch omissions.

# 🎯 Selective Reading (read-gate — open a file only when its trigger fires; read once per concern)
| File | When to Read |
|------|------|
| `figma_fullscreen/*.png` | first — overall layout, z-order, section boundaries |
| `figma_widget/<slug>.png` | per root — clearest view of shape, spacing, color (source of truth) |
| `normalize_design_code/figma_normalized.json → _screen_layout` only | before widgets — z-order/roles for stack assembly |
| `normalize_design_code/widgets/<id>_<name>.json` | per root — fills, gradientStops, effects, padding, radius |
| `analyze_layout.md` | classifying shape/anchor/sizing/Flutter widget |
| `analyze_gradient_shadow.md` | a root has gradient fill or visible shadow |
| `behavior.md` (`## Project Scaffold Conventions`) | before Screen Layout — how this project builds AppBar / body / footer / background |
| a same-type **sibling screen page** in `lib/features/**` | before Screen Layout — mirror its scaffold + background, don't invent (Issue: strange BG/UI) |
| `behavior.md` | classifying COMPLEX widgets, interactions, screen states |
| `figma_flutter_map_quick.md` | confirming the Flutter widget class |
| `.ui-workspace/flutter_helper_design.md` | before describing any gradient/shadow/blur/overflow decoration |

**Input (read these in place — never copy them to the `$FEATURE` root):**
- `figma_fullscreen/<screen>.png` + per-root `figma_widget/<slug>.png`
- `normalize_design_code/figma_normalized.json` + per-root `normalize_design_code/widgets/<id>_<name>.json` +
  `normalize_design_code/widgets/_manifest.json` (root index: `id, slug, name, type, depth, child_count, is_section, complex, in_body`)
- `.ui-workspace/figma_config.json` (`project_sources` paths + `enable_html_visualization`)

**Output:** analyze report (per-widget color map) returned to organize-figma, AND
`.ui-workspace/$FEATURE/plan/pre_plan.md` after the user confirms. (make-ui-plan turns it into plan.md.)

---

## Widget Block — one per root in `pre_plan.md` (omit sections that don't apply)
```
widget: <name>
  # Layout              ← analyze_layout.md
  shape: Pill|Rectangle|Circle|Custom · anchor: <v>-<h> · sizing: fixed(WxH)|expanded|wrap
  padding/gap (omit if 0) · layout: Column|Row|Stack|ListView|Scroll · flutter_widget: <Widget>
  # Text                ← Text widgets only
  content: "…" · l10n_hint: snake_case · text_style: <Figma style name>
  # Asset               ← Image/SVG only
  asset_type: svg|image · asset_hint: ic_snake_case
  # Decoration          ← analyze_gradient_shadow.md (skip if flat solid)
  gradient: { color_token, begin, end, colors:[0x…], stops:[…] }
  shadow:   { effect_token, offset, blur, color }
  # Behavior            ← behavior.md
  screen_type: A|B|C|D · tap: push:Route|sheet|dialog|copy|toggle|none · scroll/input/expand
  states: loading(shimmer) · empty(asset+text+cta) · error(snackbar+retry)
```

---

## Step 1 — Load & enumerate
Read `normalize_design_code/widgets/_manifest.json` first (every root normalize extracted: sections →
**every body root** (`"in_body": true`) → complex widgets, with `depth`+`complex`). Then read each
root's JSON + its PNG, map PNG↔JSON, build the inventory. Create `pre_plan.md` if missing. Skip
`_manifest.json` when listing root JSONs. If the body section has children in
`figma_normalized.json` but the manifest has zero `"in_body"` rows, the body was under-drilled →
report `NEEDS_EXTRACT: <body_id>` (caller re-runs normalize); do not guess from the body PNG alone.

### Step 1.5 — Drill-down gate (NEEDS_EXTRACT) ⚠ Issue1 escape hatch
You own the real SIMPLE/COMPLEX call (normalize's is a structural proxy). If you classify a widget
**COMPLEX** but it has **no own root JSON+PNG** in the manifest, do NOT guess from the parent PNG —
report `NEEDS_EXTRACT: <node_id>[, …]` and pause that widget. You have **no Figma MCP**; the caller
re-runs `figma-extract-agent` WIDGET mode for those ids, then re-spawns you to drill in.

## Step 2 — Analyze each root (one at a time: layout → decoration → behavior → write → next)
1. **Layout** — `analyze_layout.md` → JSON → PNG → confirm Flutter widget via `figma_flutter_map_quick.md` → write `# Layout`.
2. **Decoration** — `analyze_gradient_shadow.md` → gradient/shadow from JSON, presence from PNG (PNG wins) → write `# Decoration`.
3. **Behavior** — `behavior.md` → tap/scroll/input/expand → write `# Behavior`. New pattern not in `behavior.md` → ask user.

**Color map (mandatory):** for EVERY root record the design-token color (`dartColorConst` /
`dartGradientConst`) cross-checked against `figma_design_tokens.json`. Unmapped raw hex → `UNRESOLVED`.

**User confirmation (mandatory, show images):** SIMPLE → batch confirm · COMPLEX → one at a time
(≤2 rounds each). Missing child PNG → report `MISSING_CHILD_SCREENSHOT: <id>`, do not capture it.

## Step 3 — Analyze screen (fullscreen PNG = source of truth)
1. **Screen type** — `behavior.md` + fullscreen PNG → A/B/C/D + UX pattern.
1.5 **Reference the project scaffold BEFORE assembling (mandatory — Issue: strange BG/UI).**
   Do NOT invent the screen frame. Read `behavior.md → ## Project Scaffold Conventions`, then open a
   same-type **sibling screen page** in `lib/features/**` (the one closest in type/layout) and note how
   it builds its **AppBar**, **body** (Scaffold + SafeArea + scroll), **footer**, and **background**.
   `pre_plan.md`'s Screen Layout must mirror that structure — same AppBar style, same footer pattern,
   same background mechanism — not a novel one. If no sibling exists, say so explicitly under
   `## Screen Layout`; never fabricate a scaffold.
   **RECORD it (so make-ui-plan never re-discovers — saves a duplicate sibling/scaffold pass):** write the
   resolved pointers under a `## Scaffold Reference` block in `pre_plan.md`:
   ```
   ## Scaffold Reference
   sibling_page: lib/features/<x>/<x>_page.dart   # closest same-type screen | none
   appbar:       reuse <Widget> @ lib/...          # | none
   footer:       reuse <navbar/button> @ lib/...
   background:   <token/asset + mechanism>
   ```
2. **Background (BG) handling — apply the design's BG, never an invented one.**
   When `_screen_layout` has a `role: BACKGROUND` root (or a node literally named `BG`/`Background`):
   read that node's OWN `widgets/<id>_<name>.json` and use **its** fill as the screen background —
   solid → `Scaffold(backgroundColor:)` (mapped token); gradient → a backdrop `Container(gradient:)` at
   z0 of the Stack; image → `DecorationImage`/backdrop layer. Record the exact `dartColorConst` /
   `dartGradientConst` / asset. **Never add a background color, gradient, blur, or decorative element
   that is not in the BG node** — if the BG is just a flat color, the screen background is just that color.
3. **Assemble** from `figma_normalized.json → _screen_layout[]` (do NOT recompute grouping):
   `z_order` (low=bottom) · `role` BACKGROUND→screen background (step 2) / CONTENT→Column/Scaffold / OVERLAY→skip.
   → Stack: bg (z0) · header (AppBar/SafeArea) · body (Expanded+Scroll) · footer (Padding+Button) · overlay(skip).
   Write under `## Screen Layout` in `pre_plan.md`. Fullscreen PNG is authority for order/anchor/spacing.
4. **Verify vs PNG** — z-order, anchors, spacing, missing widgets. PNG contradicts JSON → trust PNG, mark `⚠ JSON says X, PNG shows Y → use PNG`.

### Step 3.5 — Screen states (mandatory) — ASK → CONFIRM → SAVE
Follow `behavior.md → ## Learned State Conventions`: read its `### Saved state conventions` first;
a matching `scope` → apply silently. No match → **ask the user** which states this screen has +
what each renders (`success`·`loading`·`error`·`empty`), confirm, then ask whether to **save as the
project default** (append to behavior.md). Write the result under `## Screen States`. make-ui-plan +
coding turn these into a state enum.

---

## Step 4 — HTML preview  (GENERATE when `enable_html_visualization: true`; otherwise SKIP and end)

⚠ A **required step of the skill, not an optional tail.** Read `figma_config.json → enable_html_visualization` FIRST:
- **`false` / absent** → skip this step and end the skill.
- **`true`** → you MUST produce `.ui-workspace/$FEATURE/preview.html`, then return `PREVIEW_READY: <path>`.
  **You only GENERATE it — you do NOT `open` it or confirm it with the user.** The coordinator
  (organize-figma) runs the open + "đúng/chưa → chốt" validate-and-lock gate, because a spawned subagent
  cannot pause to ask the user. Returning without `preview.html` while the flag is on is a failed run.

Work on a COPY so the shared template is never mutated (an interrupted run can't leave it dirty):
1. **Copy:** `cp .claude/skills/analyze-design/scripts/iphone17_mockup.html .ui-workspace/$FEATURE/preview.html`
   (verify with `ls -lh`). If `preview.html` already exists (a `preview_feedback` re-spawn) → edit it in place, don't re-copy.
2. From `pre_plan.md` + fullscreen PNG, write the screen markup into the COPY — edit ONLY
   `<div class="content">…</div>` + CSS under `/* Your code css start from here */`; never touch the
   shell/bezel/home-indicator. The background MUST be the BG resolved in Step 3.2 — do not invent one.
3. **`preview_feedback` given (re-spawn round)** → apply each listed discrepancy to `preview.html` + `pre_plan.md`.
4. Return `PREVIEW_READY: .ui-workspace/$FEATURE/preview.html` and end — do NOT open/confirm. The shared
   template was never edited (you worked on the copy), so no reset is needed. The coordinator opens it,
   loops with the user, and on accept locks it as the visual source of truth for coding-ui.

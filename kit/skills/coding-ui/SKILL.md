---
name: coding-ui
description: >
  Generate Flutter widget code from a detailed plan.md (+ figma_normalized.json + per-root PNGs).
  Triggered by "generate dart", "code this widget", "write flutter code". coding-ui ONLY codes —
  plan.md (from ui-plan-architect) already carries the code style, examples, screen type, mock/
  skeleton, state enum and reference files. The pipeline ENDS here: the screen-assembly run finishes
  with `flutter analyze` + fix ALL lints, then reports to organize-figma (no score/verify/golden step).
version: 5.0.0
---

# coding-ui — Flutter Code Generation

coding-ui is the executor: it turns the already-detailed `plan.md` into Dart. It does **not** decide
architecture, code style, or screen type — `ui-plan-architect` did that and wrote it into plan.md.

**Sources of truth (priority):** 1) `plan.md` (widget tree, New Token Definitions, code style +
examples, Screen States, references) · 2) **visual reference — depends on the flag:** if
`enable_html_visualization: true` → the user-signed-off `.ui-workspace/$FEATURE/preview.html`;
else → per-root PNG `figma_widget/<slug>.png` (+ fullscreen PNG for assembly) · 3) `figma_normalized.json`
(exact hex/fontSize/spacing — always governs values; never eyeball a color from a PNG/HTML).

# 🎯 Selective Reading (open a file only when its concern comes up)
| File | When to Read |
|------|------|
| `plan/plan.md` | first (Step 1) — the spine; everything else only fills gaps in it |
| `figma_widget/<slug>.png` | per widget before coding it (Step 4) |
| `figma_normalized.json` | per widget for exact hex/size/padding/radius |
| `auto_fix_rules.md` | Step 0 (silent auto-fix + ICON/BG/SHAPE rendering rules) |
| `.claude/rules/clean-code-scalability.md` · `coding-standards.md` · `l10n-reuse.md` | Step 2 before writing widgets |
| `.claude/rules/token-naming-rules.md` | Step 4 when declaring a new color/font/svg/image token |
| `.ui-workspace/flutter_helper_design.md` | before any widget with gradient/shadow/blur/overflow |
| reference files named in plan.md | ONLY when the plan is not detailed enough to code a widget |

## AGENT MODE (ui-code-agent) — one phase per invocation, NO Figma MCP
- Code strictly to plan.md + the widget PNG. Plan contradicts the PNG → `PLAN_MISMATCH: <widget> — <plan vs PNG>` (stop, report; don't fix silently).
- Bind every color/font/asset through plan.md `## New Token Definitions`; a value not listed → `PALETTE_MISS: <value>`.
- Plan too thin to code a widget → open the **reference file(s) plan.md names** (a sibling screen) and mirror its style; still unclear → report, don't improvise.
- Flip the widget's `plan.md` row Status cell to `DONE (NEW)` / `DONE (REUSE)` — keep the classification in parentheses; `SKIP` rows are never coded and stay `SKIP`. The **SCREEN ASSEMBLY** run ends with Step 5 (`flutter analyze` + lint-fix), then returns the report. No score-ui / golden.

## PRECONDITIONS
```bash
cat .ui-workspace/$FEATURE/plan/plan.md 2>/dev/null || echo "MISSING — run /make-ui-plan first"
ls .ui-workspace/$FEATURE/normalize_design_code/figma_normalized.json || echo "MISSING"
```
From `figma_config.json → project_sources` get the canonical Dart paths (colors, fonts, SVGs, images).

## Step 0 — Pre-flight
Read **`auto_fix_rules.md`**; apply silent auto-fixes + the ICON/BG/SHAPE rendering rules before coding.

## Step 1 — Internalize plan.md
Read plan.md fully: widget list (TODO/DONE) + phase order, file paths, New Token Definitions, **code
style + examples**, **screen type** (nav-index vs push), **`## Scaffold (AppBar + Footer)`** (the exact
AppBar/navbar/bottom widgets to REUSE), **mock data / skeleton** approach, **Screen States** (→ state
enum), routing, reference files. This is the spine — follow it; don't re-plan.

## Step 2 — Read rules
`.claude/rules/`: `clean-code-scalability.md` (HookConsumerWidget, page ≤300 lines, ListView.builder,
const, RepaintBoundary), `coding-standards.md` (no hardcoded string, typed Freezed models, append
l10n at end of all 4 ARB, nesting ≤3), `l10n-reuse.md` (reuse an existing key by value).

## Step 3 — Scaffold (feature screens; skip for dialog/bottom-sheet)
Follow plan.md's code style + the named reference file:
- `<name>_state.dart`: `@freezed` state with the **status enum** from plan Screen States
  (`success/loading/error[/empty]`) + `errorMessage`. Never store mnemonic/passphrase in state.
- `<name>_notifier.dart`: `@riverpod` notifier (provider name per plan, e.g. `depositCompleteProvider`);
  `build()` returns initial state; wire the mock data + loading/error/empty states per plan.
- `<name>_page.dart`: `ConsumerWidget`/`HookConsumerWidget`, `Scaffold > SafeArea`, render per status.
Then `flutter pub run build_runner build --delete-conflicting-outputs`.

## Step 4 — Code per plan.md
Order: **token writes → Phase 1 leaf → Phase 2 composite → Phase 3 screen assembly**. Per widget:
read its PNG (shape/z-order) → JSON for exact hex/size → write file → `dart analyze <file>` → fix → next.
- Tokens → `token-naming-rules.md` (append before `}`, one Edit/file, grep-verify). All user-facing text via l10n.
- AppBar + footer: use the exact widgets named in plan.md `## Scaffold (AppBar + Footer)` — REUSE, never rebuild. nav-index → `context.go` + existing bottom navbar; push → back-button AppBar + bottom button `SafeArea`+padding. Mirror the reference file if a detail is unclear.
- Page > 300 lines → extract the largest sub-tree to its own file.

## Step 5 — Finish: registries + final analyze + report
Append `[NEW]` rows only (grep-first) to `widgets.md`/`assets.md` + update `design_figma_code.md`. Flip plan.md rows to `DONE (NEW)` / `DONE (REUSE)`.
**Analyze scope:** per-widget runs use `dart analyze <file>` only (Step 4); the feature-wide command below runs ONCE, in the SCREEN ASSEMBLY run.
**Final QA (SCREEN ASSEMBLY run = pipeline end):**
```bash
flutter analyze lib/features/$FEATURE 2>&1 | tail -30
```
Fix **all** lints/errors in place, re-run until clean. Then return:
```
coding-ui complete: $FEATURE
  Files: [APPEND] app_colors.dart +K  [NEW] widgets/<name>.dart  [MODIFY] <name>_page.dart
  Registries: assets.md +Q, widgets.md +R | flutter analyze: 0 issues
  Blockers: <none | PLAN_MISMATCH | PALETTE_MISS>
  Manual: flutter pub run build_runner build --delete-conflicting-outputs
```

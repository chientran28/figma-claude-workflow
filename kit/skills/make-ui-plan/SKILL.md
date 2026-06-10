---
name: make-ui-plan
description: >
  Resolves the confirmed Pre-Plan from analyze-design into an EXTREMELY DETAILED, actionable
  coding plan. Identifies new vs reusable tokens, studies sibling screens for code style, and
  writes plan/plan.md so coding-ui only has to execute it — code style + small examples, screen
  type, mock/skeleton, state enum, routing and reference files all live in plan.md. Triggers on:
  "/make-ui-plan", "write ui plan", "tạo plan UI", or organize-figma Step 3. REQUIRES: $FEATURE + Pre-Plan.
version: 4.0.0
---

# make-ui-plan — UI Plan Author

Takes `pre_plan.md` (from analyze-design) and produces the full coding plan. Writes ONLY
`.ui-workspace/$FEATURE/plan/plan.md`. No Dart. **The plan must be detailed enough that coding-ui
never has to re-analyze** — it carries the code style + small examples, the screen type, mock/skeleton,
the state enum, routing, and the reference files to mirror. If a part is thin, coding-ui falls back to
reading the reference files you name.

## Inputs
- `feature` (snake_case, required) · `.ui-workspace/$FEATURE/plan/pre_plan.md` (hints: `color_token`, `text_style`, `asset_hint`,
  `l10n_hint`, `tap`, `## Screen States`, `## Scaffold Reference`) · `figma_config.json → project_sources`
  (real Dart/asset paths) · `.ui-workspace/exist_design/widgets.md` + `assets.md` (the reuse registry).
  **make-ui-plan is the SOLE consumer of `exist_design/` for the reuse-vs-new decision — no other
  pipeline skill reads it.** Empty/missing registry while the Pre-Plan needs a shared widget/asset → ask
  once / suggest `/get-exist-design`.
- **Visual reference (NO image load):** `pre_plan.md` is the distilled visual analysis — work from it.
  When `enable_html_visualization:true`, read `.ui-workspace/$FEATURE/preview.html` (HTML text, cheap)
  for layout/spacing. **Never load the fullscreen or per-widget PNG** — analyze already did the image
  recognition; re-loading it here is the duplicate this skill exists to avoid. Exact geometry →
  `figma_layout.json` + `figma_normalized.json → _screen_layout`.
Missing feature/Pre-Plan → ask once. Do not invent widgets.

## Step 1 — Resolve tokens + widgets: NEW vs REUSE  (the reuse registry lives here)
**1a.** Read `.ui-workspace/$FEATURE/plan/pre_plan.md`; collect `color_token`, `text_style`, `asset_hint`, `l10n_hint`, widget names, `tap`.
**1b. Grep** (token paths from `figma_config.json → project_sources`; widget/asset reuse from
`exist_design/*.md`, per `token-naming-rules.md §A`):
| Hint | Grep | REUSE | NEW |
|---|---|---|---|
| color/hex | `CLR_` key or `0xFF<hex>` in color file | existing const | not found |
| text_style | `FNT_` key / style in font file | existing const | not found |
| asset_hint | `ICO_`/`AST_` key in svg/image file **and** `exist_design/assets.md` | existing const | not found |
| widget name | `WGT_` / class in `exist_design/widgets.md` (shared + feature widgets) | reuse that widget | build new |
| l10n_hint | `"value"` in `intl_en.arb` (reuse key if value exists — `l10n-reuse.md`) | existing key | not found |
| tap | router file (`route-naming-rules.md`) | existing route | not found |
**1c.** Classify each REUSE vs NEW. **Reuse-first: default to REUSE — mark `NEW` only when no reasonable
match exists in shared widgets OR sibling-feature widgets in `exist_design/widgets.md` (fewer new
widgets = less code = faster).** No NEW for a type → write `SKIP`. Has NEW → read `token-naming-rules.md §B`,
write the exact dart line + `// KEY_comment` + target file into `## New Token Definitions`; call `/get-asset-figma` for any new image/icon.
Reused widgets from `exist_design/widgets.md` go under `### Reused widgets` with their file path.

## Step 2 — Study sibling screens (code style + examples) ⚠
**Reuse analyze's pointer, don't re-discover:** read `pre_plan.md → ## Scaffold Reference → sibling_page`
— the same-type sibling analyze already found. Open its **notifier + state** (analyze read the page for
scaffold, not these) and lift the code style: notifier/provider naming, `@freezed` state shape, how mock
data + skeleton + state enum are done, navigation style. Embed a **small** snippet in the plan. Only grep
`lib/features/` yourself if `## Scaffold Reference` recorded `none`. Name these files under
`## Reference Files` so coding-ui can open them if the plan is thin.

## Step 2b — Resolve AppBar + Footer by screen type (REUSE, don't rebuild) ⚠
**Start from `pre_plan.md → ## Scaffold Reference`** — analyze already resolved `appbar`/`footer`/`background`
against the sibling; REUSE those exact widgets/paths. Only when a field is missing/`none`: read
`.claude/skills/analyze-design/behavior.md → ## Project Scaffold Conventions → ### Saved scaffold
conventions` (entry matching the Screen Type → reuse), else find it in the sibling and **append** a block
there for the next screen. Rule: **nav-index** → `context.go` + reuse the existing bottom navbar widget
(never rebuild) + AppBar like siblings; **push** → back-button AppBar identical to siblings + bottom
button in `SafeArea`+padding. Write the resolved widgets/paths into `## Scaffold (AppBar + Footer)` (Step 3).

## Step 3 — Write plan/plan.md (the detailed template)
```markdown
# UI Plan — $FEATURE
## Screen: <screen_name>
## Created: <ISO date>
## Status: IN_PROGRESS

## Screen Type: nav-index | push
<!-- nav-index → context.go + reuse existing bottom navbar + AppBar like siblings.
     push → AppBar identical to siblings + bottom button SafeArea + padding. -->

## Reference Files   <!-- sibling screens coding-ui mirrors for style -->
- lib/features/<sibling>/<sibling>_notifier.dart — same type, copy provider+state shape
- lib/features/<sibling>/<sibling>_page.dart     — layout/navigation pattern

## Scaffold (AppBar + Footer)   <!-- from Step 2b — REUSE, don't rebuild -->
- appbar: <none | reuse <Widget> @ lib/...>  · footer: <reuse navbar @ lib/... | bottom button SafeArea+padding>
- nav: context.go (nav-index) | context.push (push)

## Code Style   <!-- conventions + ONE small example, drawn from the reference -->
- Notifier: `@riverpod class <Feature> extends _$<Feature>` → `<feature>Provider`
- State: `@freezed` with a status enum + `errorMessage`
```dart
@freezed
class <Feature>State with _$<Feature>State {
  const factory <Feature>State({ @Default(<F>Status.loading) <F>Status status, String? errorMessage, ... }) = _<Feature>State;
}
enum <F>Status { loading, success, error }   // from Screen States
```

## Screen States   <!-- from analyze 3.5 -->
- success: <content> · loading: <skeleton/shimmer> · error: <msg+retry> · empty: <if list>

## Mock Data & Skeleton
- mock data: defined in <where, e.g. notifier build()> · skeleton: <widget/pkg> at <where>

## New Token Definitions   <!-- SKIP a type if nothing new -->
### Color / ### TextStyle / ### Assets (→ app_svgs + pubspec) / ### L10n (intl_en→es/ja/zh) / ### Routes
<!-- each NEW: exact dart line + // KEY_comment + target file -->
### Reused widgets
- Snackbar: REUSE (lib/...) · <Widget>: NEW

## Widget Phase
| Phase | Widget | Class | Position | Key Attributes | Behavior | Status |
|---|---|---|---|---|---|---|
| 1 | CheckIcon | SIMPLE | body·center | SvgPicture(AppSVGs.icCheck)·size:80 | static | Reuse |
| 2 | InfoCard | COMPLEX | body·below icon | Container(gradient)·pad h16v12 | static | New |
| 3 | SCREEN ASSEMBLY | — | full screen | Stack·SafeArea·AppBar | scroll:v | New |
<!-- Status lifecycle: this skill writes the classification (New / Reuse / SKIP).
     coding-ui flips each coded row to DONE (NEW) / DONE (REUSE) — classification kept in parentheses.
     SKIP rows are never coded and stay SKIP; pipeline-gate treats DONE… and SKIP as complete. -->

## Widget Tree   <!-- from pre_plan.md, expanded -->
## Source of Truth: <!-- enable_html_visualization:true → .ui-workspace/$FEATURE/preview.html ; else → figma_fullscreen/<screen>.png -->
```

## Rules
- Writes ONLY `plan/plan.md`. Never invent widgets not in the Pre-Plan. For each NEW token write the
  exact code line + a `// KEY_comment`. Coding agent must follow plan.md strictly — so make it complete.

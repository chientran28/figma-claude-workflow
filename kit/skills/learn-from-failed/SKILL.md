---
name: learn-from-failed
description: >
  Learn from real Flutter/UI bugs. Triggers on: "fix UI", "learn from failed",
  "UI looks wrong", "save this bug". Collects the bug → re-reads the screen's plan.md +
  fullscreen/widget screenshot → fixes (HTML-preview verify loop when enable_html_visualization,
  else proposes text options) → applies the Dart fix → saves the correct pattern to
  .ui-workspace/flutter_helper_design.md and the error code to .ui-workspace/ui_failed.md.
version: 2.1.0
---

# learn-from-failed — Collect & Memorize UI Bugs

Turn every UI bug into long-lived knowledge so the agent self-corrects next time. After a cycle,
coding-ui / flutter-ui-agent read `ui_failed.md` + `flutter_helper_design.md` to avoid the repeat.

## Step 0 — Load meta-learnings (always first)
Read `.ui-workspace/learnings.md` — **Common Misclassifications**, **User Description → Category
Hints**, **Process Insights**. A match → reuse it in Step 3; skip questions it already answers.

## Step 1–2 — Collect the bug
**Pre-fill mode (called by orchestrator):** if context keys are supplied, skip the questions.
Keys: `$FEATURE` · `$LOCATION` (file/widget) · `$CODE_SNIPPET` · `$SCREEN` · `$PROBLEM` · `$EXPECTED`.
Any missing → ask only for those; all present → go straight to Step 2.5.

**Interactive mode** — ask sequentially (not all at once):
1. "Which file/widget has the bug?" → `$LOCATION` (+ `$CODE_SNIPPET`, `$SCREEN`). Path given → read it.
2. "What is wrong? How does the UI look incorrect?" → `$PROBLEM`.
3. "What should it look like?" → `$EXPECTED`.

## Step 2.5 — Ground the fix in the design (when `$FEATURE`/`$SCREEN` known)
Never fix from memory. Read `.ui-workspace/$FEATURE/plan/plan.md` (screen type, tokens, code style);
multimodal-Read the `figma_fullscreen/<screen>.png` (+ the buggy `figma_widget/<slug>.png`) — what it
SHOULD look like; read `$LOCATION` — what it DOES. The fix closes that gap. No `$FEATURE` → skip, use `$PROBLEM`+`$EXPECTED`.

## Step 3 — Diagnose & match prior knowledge
1. Read `.ui-workspace/ui_failed.md` — similar past code? → show its fix, ask "Does this match `[UI-XXX]`?". Else fresh analysis.
2. Classify the category:

| Code | Indicators | Code | Indicators |
|---|---|---|---|
| `LAYOUT` | misaligned, wrong padding, bad Row/Column | `GRADIENT` | gradient too dark/light, wrong Opacity |
| `OVERFLOW` | clipped, RenderFlex overflow | `SHADOW` | shadow/inner-shadow/blur wrong |
| `SCROLL` | can't scroll, nested-scroll conflict | `ANIM` | jank, wrong timing, not playing |
| `COLOR` | wrong/hardcoded color, dark mode | `ASSET` | image not loading, wrong scale/ratio |
| `TEXT` | wrong font/size/line-height/truncation | `COMP` | widget reused wrong, wrong constructor |

## Step 3.5 — Produce the fix (mode by `enable_html_visualization` in `figma_config.json`)

**Mode A — HTML-preview verify loop** (`true` **and** `$FEATURE` known) — iterate visually, then write Dart:
1. **Copy** the template to a THROWAWAY file (a distinct name so it never clobbers analyze's persistent
   `preview.html`): `cp .claude/skills/analyze-design/scripts/iphone17_mockup.html .ui-workspace/$FEATURE/preview_fix.html`
2. Patch ONLY the buggy region into the COPY — `<div class="content">…</div>` + CSS under
   `/* Your code css start from here */`; never touch the phone shell/bezel/home-indicator.
3. **Auto-open for the user:** `open .ui-workspace/$FEATURE/preview_fix.html`. Ask: "Does this match the intended design? List anything still off."
4. Not accepted → re-read plan.md + PNG, update the copy, reopen (≤3 rounds).
5. **Accepted →** translate the HTML/CSS into the Dart fix at `$LOCATION` (real tokens from plan.md
   New Token Definitions / `project_sources`, not raw hex) → **delete the throwaway** (`rm .ui-workspace/$FEATURE/preview_fix.html`). Go to Step 4.

**Mode B — Text options** (`false`, or no `$FEATURE`) — propose 2–4 fixes:
```
Analysis: [why the bug occurs]
A) [name] — [one-line]   Code: [snippet]
B) … · C) … · D) I want to enter a custom fix
```

## Step 4 — Apply (Dart)
Mode A → apply the derived fix. Mode B → after the user picks A/B/C/D (or types one) → edit `$LOCATION`.
Save-only (no code change) → skip the edit. After editing, `dart analyze` runs via the
`dart-analyze-feedback` hook — wait for it; render/overflow errors → check injected known patterns first.

## Step 5 — Save the pattern → `.ui-workspace/flutter_helper_design.md`
Append only if no section with the same root cause exists (else update only if better). ≤25 lines, relevant code only.
```markdown
## <N+1>. [CATEGORY] — <short bug name>
> Error code: `UI-<CATEGORY>-<NNN>` · First seen: <YYYY-MM-DD>
**Symptom:** … · **Cause:** … 
**Correct fix:** ```dart <relevant code> ``` · **Avoid:** ```dart // ❌ <wrong pattern> ```
```

## Step 6 — Save the code → `.ui-workspace/ui_failed.md`
Append (never overwrite). Number per category: read highest existing → +1 (new category starts `001`).
```markdown
| UI-<CATEGORY>-<NNN> | <short bug name> | <root cause, 1 line> | `flutter_helper_design.md §<N>` |
```

## Step 7 — Report
`✓ Saved: UI-<CATEGORY>-<NNN> — <bug>` + the §N updated + the new row. Next time the agent applies it automatically.

## Step 8 — Update `learnings.md` (MANDATORY every cycle)
Append ONE line under `## Process Insights` — `[CATEGORY] YYYY-MM-DD: <takeaway>`.
`CATEGORY` ∈ `MISCLASSIFY` (wrong category first) · `PATTERN_HINT` (phrase→code) · `PROCESS`
(workflow change) · `KNOWLEDGE_GAP` (bug class not yet in flutter_helper_design.md). Don't duplicate
bug patterns here. `knowledge-eval.sh` auto-archives entries >30 days — no manual pruning.

## How other agents read `ui_failed.md`
On a node that may match a known bug: read `ui_failed.md` → matching `Root cause` → open its
`flutter_helper_design.md` §N → apply "Correct fix". Not found → handle normally, don't ask. Auto-check:
gradient+opacity→`UI-GRADIENT-*` · `INNER_SHADOW`→`UI-SHADOW-*` · `Column` in `Scaffold.body` no
scroll→`UI-SCROLL-*` · `Text` in `Row` no `Expanded`→`UI-OVERFLOW-*`.

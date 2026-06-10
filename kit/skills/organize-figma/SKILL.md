---
name: organize-figma
description: >
  Master coordinator for the Figma → Flutter screen pipeline. Loads in the MAIN conversation
  on a Figma node-id link, a screen screenshot, or "code/build/implement screen". Runs 4 steps:
  1 normalize → 2 analyze → 3 plan → 4 code. Every heavy step runs in an ISOLATED subagent, so
  the coordinator stays light all run — no manual /compact. The pipeline ENDS at coding: the code
  agent's last action is `flutter analyze` + fix all lints + report (NO score/verify step).
  Routes work, verifies each step, passes paths on. Writes no code, no plan.md. Retries a failed
  step ≤2. Never spawns organize-figma recursively.
version: 5.1.0
---

# organize-figma — Pipeline Coordinator

Pure routing: spawn the subagent that does the work, verify its output, pass paths to the next step.
The heavy load (Figma MCP payloads, PNGs, big JSONs, Dart) lives **inside subagents** — this context
holds only small reports + paths, so no `/compact` is needed.

**Rules:** never call Figma MCP here · never open a PNG / `figma_*.json` / per-root
`normalize_design_code/widgets/*.json` here · write no code, no plan.md content — the ONLY plan.md
write allowed here is flipping the `## Status` line when closing the pipeline (Step 4 Verify) · never ask "Proceed?" once plan.md exists.

## TRIGGER
A Figma URL with `node-id=` · a screen screenshot · "code/build/implement screen".
→ parse `$NODE_ID` (`421-1289`/`421%3A1289` → `421:1289`; screenshot-only → skip).
→ **`$FEATURE` = Figma LINK-NODE name (snake_case)** ⚠Issue2. Order: explicit user name → link-node
name → ask once. NEVER the git branch or an existing folder (that was the `home_op2` bug). You don't
know the node name yet → leave `$FEATURE` empty; Step 1 resolves it, then read it from `pipeline.md`.

## Coordinator reads only (small routing files)
`pipeline.md` (state) · `plan/plan.md` (Status + Widget Phase) · `normalize_design_code/widgets/_manifest.json`
(root count) · `figma_asset/mapping.json` (entry count). Everything else → pass by path to the subagent.

---

## STEPS — each: spawn 1 subagent → verify output → on fail retry (≤2) → pass paths on

### 1 — normalize  ·  Agent `figma-extract-agent` (runs `/normalize-figma-file`)
- **In:** `$NODE_ID` (+ `feature` only if user named it) + `figma_file_id` from `figma_config.json`. No URL → copy screenshot into `figma_fullscreen/`, skip MCP.
- **Out:** owns Figma MCP. Resolves feature/screen from the LINK NODE; writes 3 JSONs + fullscreen PNG + **one PNG+JSON per root** (sections → **every body root** → complex widgets, drilled) under `normalize_design_code/` + `normalize_design_code/widgets/_manifest.json`.
- **Auto:** `mapping.json` missing/empty → `/get-asset-figma feature=$FEATURE node_id=$NODE_ID`.
- **Verify:** 3 JSONs + `normalize_design_code/widgets/_manifest.json` + fullscreen PNG exist; one `figma_widget/` PNG per root (minus `MISSING_WIDGET_PNG`); body fully drilled (manifest has `"in_body":true` rows when the body has non-leaf children); **no stray `$FEATURE/figma_normalized.json` or `$FEATURE/widgets/`**; `mapping.json` has entries.
- **Save state:** `printf "feature: %s\nnode_id: %s\nscreen: %s\nnode_name: %s\nfigma_url: %s\n" … > .ui-workspace/$FEATURE/pipeline.md`. Print `CHECKPOINT — normalize done`.
- **Fail:** re-spawn (≤2) → still missing → STOP + exact error.

### 2 — analyze  ·  Agent `analyze-design-agent`
- **In:** Step 1 paths (normalized JSON, tokens, layout, `_manifest.json`, fullscreen + per-root PNGs, `figma_config.json`). Re-spawn rounds (HTML gate) add `preview_feedback=<user discrepancies>`.
- **Out:** classifies each root SIMPLE/COMPLEX, maps colors/shadows, picks behavior, **determines screen states (success/error/loading)**, records the sibling-screen scaffold + BG it mirrors under `## Scaffold Reference` (no invented UI — make-ui-plan reuses this), writes `plan/pre_plan.md` — AND, when `enable_html_visualization:true`, **GENERATES** `preview.html` and returns `PREVIEW_READY: <path>`. The agent does NOT open or confirm the preview — the coordinator does (HTML gate).
- **HTML gate (coordinator-owned — only when `enable_html_visualization:true`):** on `PREVIEW_READY` → `open .ui-workspace/$FEATURE/preview.html`, ask the user **"Thiết kế đúng chưa? đúng → chốt · chưa → liệt kê điểm sai"**. *chưa* → re-spawn the agent with `preview_feedback=<notes>` (≤2 rounds) → reopen → re-ask. *đúng* → stamp `pre_plan.md` with `## Source of Truth: preview.html (confirmed <date>)` (lock), then Step 3.
- **Verify:** the agent's ✓ lines + `plan/pre_plan.md` exists; **if `enable_html_visualization:true`, `preview.html` exists AND was user-confirmed via the gate above** (flag on but no preview / not confirmed → re-run the gate or re-spawn; do not pass to Step 3).
- **Drill/fail:** `NEEDS_EXTRACT: <id>[,…]` → re-spawn `figma-extract-agent` WIDGET mode (`widget_ids=<ids>`) → re-spawn analyze (≤2). `MISSING_CHILD_SCREENSHOT` → same. Agent down → run `analyze-design/SKILL.md` inline.

### 3 — plan  ·  Agent `ui-plan-architect` (runs `make-ui-plan`)
- **In:** confirmed `pre_plan.md` + `figma_config.json → project_sources`. (make-ui-plan is the sole consumer of the `exist_design/*.md` reuse registry — it reads it directly; the coordinator does not pass or open it.)
- **Out:** resolves NEW vs REUSE tokens, expands widget tree, records source-of-truth paths + routing, writes `plan/plan.md` (`## New Token Definitions` + `## Widget Phase`, `Status: IN_PROGRESS`).
- **Verify:** plan.md has both tables. **Fail:** re-spawn (≤2, same budget as every step); agent down → `make-ui-plan/SKILL.md` inline; `NEEDS_REVIEW` → log one line, continue.

### 4 — code  ·  Agent `ui-code-agent` (runs `coding-ui`)  — LAST step
- **In:** `plan.md` Widget Phase rows (New Token Definitions = color/font/asset authority) + per-root PNG + normalized JSON + `mapping.json`.
- **Out:** for each row in order (SIMPLE → COMPLEX → SCREEN ASSEMBLY) spawn 1 `ui-code-agent` → it codes the widget, flips its row's Status cell to `DONE (NEW)` / `DONE (REUSE)` — keep the classification in parentheses, never erase it. Rows marked `SKIP` are never coded and stay `SKIP`.
  The SCREEN-ASSEMBLY agent's **final action = `flutter analyze` over the feature + fix ALL lints**, then report.
- **Verify:** every row `DONE (…)` or `SKIP` + final agent reported `flutter analyze` clean → coordinator sets `plan.md` `## Status: DONE`.
- **Fail:** `PLAN_MISMATCH` → fix plan row / re-run Step 3 for it, re-code. `PALETTE_MISS` / missing asset → `/get-asset-figma` once or re-run Step 3, re-spawn. Agent down → `coding-ui/SKILL.md` inline (`inline-fallback`), still flip the row.

---

## AUTOMATION — unattended EXCEPT
Workspace/`exist_design/` missing → STOP (run `/init-ui-workspace` + `/get-exist-design`) · link
node has no name AND no explicit `$FEATURE` → ask once · Figma API error/node not found → STOP +
error · `exist_design/*.md` empty AND user says "didn't reuse" → `/get-exist-design`, resume · asset
missing → `/get-asset-figma`, resume · `NEEDS_EXTRACT` → WIDGET-mode re-extract + re-analyze (≤2) ·
UI wrong post-run → offer `/learn-from-failed`.

## ✅ CHECKLIST — re-print with [x]/[ ] before any "done" report
```
[ ] 1 normalize — figma-extract-agent returned paths; 3 JSONs + normalize_design_code/widgets/_manifest.json + fullscreen PNG + one figma_widget/ PNG per root; body fully drilled ("in_body" rows); NO stray $FEATURE-root figma_normalized.json/widgets/; mapping.json has entries; pipeline.md saved (feature = LINK-NODE name)
[ ] 2 analyze   — ✓ lines; plan/pre_plan.md exists + ## Scaffold Reference recorded; preview.html exists AND user-confirmed via coordinator HTML gate IF enable_html_visualization:true; NEEDS_EXTRACT resolved
[ ] 3 plan      — plan.md: ## New Token Definitions + ## Widget Phase; Status: IN_PROGRESS
[ ] 4 code      — every Widget Phase row = DONE (…) or SKIP; final `flutter analyze` clean; coordinator set Status: DONE
```

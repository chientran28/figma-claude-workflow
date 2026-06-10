# normalize-figma-file — Python Normalizer

**Requires:** `$NODE_ID` from caller context. `$FEATURE` is **optional** — when omitted it
defaults to the Figma **link-node name** (see Step 0c). Never invent a feature name.

> **Runs inside `figma-extract-agent`** (an isolated subagent that owns the Figma MCP). All
> the heavy MCP payloads (`get_design_context`, `get_nodes_info`, `save_screenshots`) are
> absorbed here, so the main `organize-figma` context never sees them — that is what keeps
> the coordinator light across sections (no manual `/compact` needed).

**Two modes:**
- **SCREEN mode** (default) — full extraction of a link node: root → header/body/footer →
  **every root inside the body (the body is ALWAYS fully drilled)** → each complex widget,
  drilled down recursively.
- **WIDGET mode** (escape hatch) — `widget_ids=A,B,C` given → extract JSON + PNG for *only*
  those node ids. Invoked when `analyze-design` reports `NEEDS_EXTRACT: <id>` for a COMPLEX
  widget that was not drilled deeply enough in the first pass.

> ⚠ **PATH CONTRACT (Issue: stray files).** Every normalize artifact lives under
> `.ui-workspace/$FEATURE/normalize_design_code/` (the normalized JSON, the per-root `widgets/`
> dir, and `_manifest.json`). **NEVER write `figma_normalized.json` or a `widgets/` folder at the
> `$FEATURE` root** — that produces duplicate stray files. Read these files **in place**; do not
> copy them up a level "for convenience". If a stray `$FEATURE/figma_normalized.json` or
> `$FEATURE/widgets/` exists from an older run, delete it (see Step 1).

> ⚠ **`_manifest.json` is preprocessor output — do NOT hand-edit it.** Its schema is fixed
> (`{id, slug, name, type, depth, child_count, is_section, complex, in_body}`). To add/extract a
> root, re-run the preprocessor or use WIDGET mode (which appends a row programmatically). Never
> hand-add fields or hand-prune rows.

**Output (SCREEN mode):**
- `figma_code/figma_design_tokens.json` · `figma_code/figma_layout.json`
- `normalize_design_code/figma_normalized.json` — includes a top-level `_screen_layout` block
  (preprocessor Pass 6): z-order, layout type and visual role per root — consumed by analyze-design
  (role/z-order) and make-ui-plan (exact geometry).
- `normalize_design_code/widgets/<id>_<name>.json` — **one per root**: every section
  (header/body/footer), **every non-leaf root inside the body** (the body rule: the body's
  direct children are ALWAYS each exported, regardless of the complex heuristic), and every
  complex widget below them (recursive drill-down, produced by `figma_preprocessor.py` Pass 7).
- `normalize_design_code/widgets/_manifest.json` — `{id, slug, name, type, depth, child_count, is_section, complex, in_body}` per root. **Drives the PNG-capture loop.**
- `figma_widget/<slug>.png` — **one per root** in the manifest (scale 3).
- `figma_fullscreen/<screen_name>.png` (scale 2).

> Every step that produces a file MUST verify with `ls -lh <path>`. Missing → retry; do not skip.

---

### Step 0 — Resolve feature + screen name from the LINK NODE  ⚠ (Issue 2) — DO THIS FIRST

`$FEATURE` roots every write below (`.ui-workspace/$FEATURE/…`), so resolve it **before** Step 0a/0b.
Use metadata only — never read a `$FEATURE`-rooted file here (that was the circular-dependency bug).

1. `get_metadata([$NODE_ID])` → the link node's `name` (metadata only, no file dependency).
2. `screen_name = slug(name)` — lowercase, non-alphanumerics → single `_` (same rule as
   `figma_preprocessor._slugify`). e.g. `"Deposit Complete"` → `deposit_complete`.
3. **`$FEATURE` default = `screen_name`.** Keep a caller-supplied `$FEATURE` only if the user
   *explicitly* named it; otherwise use `screen_name`. NEVER fall back to a pre-existing folder or
   the git branch (that is the `home_op2` bug — the link node was `deposit_complete`).
4. Echo the resolved pair: `feature=<…>  screen=<screen_name>  (from link node "<name>")`.

### Step 0a — Design Tokens  (now `$FEATURE` is known)

```
PARALLEL: get_variable_defs() · get_styles() · get_fonts()
THEN:     export_tokens(format="json")
```
Write → `figma_code/figma_design_tokens.json`

### Step 0b — Layout

```
get_design_context(nodeId="$NODE_ID", detail="full", depth=3, dedupe_components=true)
```
Write → `figma_code/figma_layout.json`

---

### Step 1 — Verify Inputs (+ purge any stray files from an older run)

```bash
ls -lh .ui-workspace/$FEATURE/figma_code/figma_design_tokens.json \
        .ui-workspace/$FEATURE/figma_code/figma_layout.json
# Purge stray duplicates that older runs wrote to the $FEATURE root (Issue: stray files).
# The canonical copies live under normalize_design_code/ — these top-level ones must not exist.
rm -f  .ui-workspace/$FEATURE/figma_normalized.json
rm -rf .ui-workspace/$FEATURE/widgets
```
Missing either input → re-run Step 0a/0b. Missing `figma_preprocessor.py` → stop.

---

### Step 2 — Run Preprocessor

```bash
python3 .claude/commands/scripts/figma_preprocessor.py $FEATURE
```
Produces (all under `normalize_design_code/`): `figma_normalized.json` + `widgets/<id>_<name>.json`
(recursive roots) + `widgets/_manifest.json`. **Body rule:** Pass 7 force-exports every non-leaf
direct child of the `body` node as its own root (look for the `(body-root)` lines in the output and
`"in_body": true` rows in the manifest) — so the body is never collapsed into a single screenshot.
Do not write any of these to the `$FEATURE` root.

---

### Step 3 — Handle Preprocessor Failures (skip if Step 2 succeeded)

1. Report: `Node "<name>" has unknown key "<key>"`
2. Ask user which Flutter widget to use (Enter = decide from `FIGMA_FLUTTER_MAP.md`)
3. If confirmed correct → update `figma_preprocessor.py` + `FIGMA_FLUTTER_MAP.md`
4. Retry up to 3 times. Still failing → show full error, stop.

---

### Step 4 — Screenshots (root of link node → every drilled root)

**4a — Fullscreen (root of the link node):**
```
save_screenshots([{ nodeId: "$NODE_ID", outputPath: "figma_fullscreen/<screen_name>.png", scale: 2 }])
```

**4b — One PNG per root from the manifest (drives the drill-down image set):**
Read `normalize_design_code/widgets/_manifest.json`. Build ONE `save_screenshots` batch with an
entry for every root in it — sections (`header`/`body`/`footer`/…), the roots inside the body,
and every complex widget below them:
```
save_screenshots(
  manifest.map(r => ({ nodeId: r.id, outputPath: "figma_widget/" + r.slug + ".png", scale: 3 }))
)
```
- Batch in chunks of ≤ 20 if the manifest is large.
- A node that fails to render (e.g. an instance-internal id) → log `MISSING_WIDGET_PNG: <id>` and
  continue; do NOT abort the batch.

**4c — Per-root JSON is already written** by the preprocessor (Pass 7). Do not recompute it here.

---

### Step 5 — Final Checkpoint (SCREEN mode)

```
.ui-workspace/$FEATURE/
├── figma_code/
│   ├── figma_design_tokens.json
│   └── figma_layout.json
├── normalize_design_code/              ← the ONLY home of normalized artifacts
│   ├── figma_normalized.json
│   └── widgets/
│       ├── _manifest.json
│       ├── <id>_header.json            ← section
│       ├── <id>_body.json              ← section
│       ├── <id>_footer.json            ← section
│       ├── <id>_<bodyRoot>.json        ← EVERY non-leaf child of body ("in_body": true)
│       └── <id>_<complexWidget>.json   ← complex widgets below the body roots (recursive)
├── figma_widget/
│   └── <slug>.png                      ← one per manifest root (scale 3)
└── figma_fullscreen/
    └── <screen_name>.png               ← root of the link node (scale 2)
```
Verify:
- `normalize_design_code/figma_normalized.json` + `normalize_design_code/widgets/_manifest.json` exist.
- `figma_widget/` has one PNG per manifest root (minus any `MISSING_WIDGET_PNG`).
- **Body fully drilled:** the manifest has the body section AND one `"in_body": true` row per non-leaf body child.
- **No strays:** `ls .ui-workspace/$FEATURE/figma_normalized.json` and `.../widgets` both return *not found*.

Return the manifest path + the resolved `feature`/`screen`.

---

### WIDGET MODE — on-demand drill-down (escape hatch for `NEEDS_EXTRACT`)

Invoked as `/normalize-figma-file feature=$FEATURE node_id=$NODE_ID widget_ids=A,B,C` when
`analyze-design` flags a COMPLEX widget that lacks its own root JSON+PNG.

For **each** id in `widget_ids`, derive the slug **identically to SCREEN mode** (the preprocessor's
rule): `slug = id.replace(":", "_") + "_" + slugify(name)` — so both modes share one filename
convention and analyze keys off the same `slug`:
1. **JSON (no MCP):** find that node's subtree in `normalize_design_code/figma_normalized.json`
   (already on disk) and write it to `normalize_design_code/widgets/<slug>.json` if absent.
   Append a row to `normalize_design_code/widgets/_manifest.json` with that same `slug`
   (+ `id, name, depth, complex, in_body:false`). Never write to the `$FEATURE` root.
2. **PNG (MCP):** `save_screenshots([{ nodeId: "<id>", outputPath: "figma_widget/<slug>.png", scale: 3 }])`.
3. Failure to render → `MISSING_WIDGET_PNG: <id>`, continue.

Return the list of newly-written `widgets/*.json` + `figma_widget/*.png` so the caller can
re-spawn `analyze-design` over just those drilled widgets.

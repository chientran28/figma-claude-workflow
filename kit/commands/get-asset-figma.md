# get-asset-figma — Figma Asset & Icon Extractor

**Input:** Figma node link OR `normalize_design_code/figma_normalized.json` | **Requires:** Figma MCP, Read/Edit/Write  
**Output:** Files in `assets/` + constants in `AppSVGs`/`AppImages` + `assets.md` updated

> **SVG RULE:** Always `format: "SVG"` explicitly — MCP default is PNG.  
> **VERIFY RULE:** `ls -lh <path>` after every file write.

## MODES
| Args | Mode |
|------|------|
| none / `frame=...` / `node_id=...` | **MODE A** — receive ANY screen/frame node link → auto-discover icon + image nodes inside it |
| `feature=<f> node_id=<id>` | **MODE B** — export screen assets → `mapping.json` |

> **MODE A no longer assumes the node only contains assets.** It accepts a full screen node and recursively walks the subtree to locate every icon/image node, ignoring layout/text/container nodes.

---

## When organize-figma calls this
- **MODE B** — `organize-figma` Step 1 auto-runs `/get-asset-figma feature=$FEATURE node_id=$NODE_ID`
  when `.ui-workspace/$FEATURE/figma_asset/mapping.json` is missing/empty (screen asset export).
- **MODE B** — re-run on a `PALETTE_MISS` / missing-asset blocker from coding.
- **MODE A** — manual: pass a Figma frame/screen link to harvest its icons + images into the project.

## PRE-CHECK (MODE A)
Read `.ui-workspace/figma_config.json`. Stop if:
- No `frame=`/`node_id=` arg AND no `normalize_design_code/figma_normalized.json` → *Pass a Figma frame/screen node link or run `/normalize-figma-file` first*
- `.ui-workspace/exist_design/assets.md` missing → *Run `/get-exist-design` first*

**is-first-time = true** when `project_sources.asset` paths are empty.

---

## STEP 1 — Identify Assets from Node
If node link exists → call Figma MCP in parallel: `get_node` + `scan_nodes_by_types(["VECTOR","BOOLEAN_OPERATION","RECTANGLE","COMPONENT","INSTANCE","FRAME"])`  
Otherwise → read `normalize_design_code/figma_normalized.json`.

| Type | Signals |
|------|---------|
| **SVG icon** | Name `ic_*`/`icon_*`/`Icon/*`; type `VECTOR`/`BOOLEAN_OPERATION`; or COMPONENT with only VECTOR children |
| **Image** | Type `IMAGE`/RECTANGLE with image fill; name `img_*`/`bg_*`/`photo_*`/`banner_*`/`illustration_*` |
| **Ambiguous** | Ask user |

**Output:** Asset list with `nodeId`, `name`, `type`.

---

## STEP 2 — Classify New vs Existing (early exit if none new)
Read `.claude/rules/token-naming-rules.md` **§A** for grep commands and file paths.

```bash
grep "ICO_" <project_sources.asset.svg.dart_file>
grep "AST_" <project_sources.asset.image.dart_file>
grep "ICO_\|AST_" .ui-workspace/exist_design/assets.md
```

Build mapping table (`new` / `existing` per asset). **If ALL existing → report "nothing new" and END.**

| Figma node | Registry key | Dart constant | Target path | Status |
|-----------|-------------|--------------|-------------|--------|
| `ic_wind` | `ICO_weatherWind` | `icWind` | `assets/vectors/ic_wind.svg` | new |

---

## STEP 3 — Download New Assets
```
save_screenshots(items=[{ nodeId, outputPath: "assets/vectors/<n>.svg", format: "SVG" }])
save_screenshots(items=[{ nodeId, outputPath: "assets/images/<n>.png",  format: "PNG", scale: 2 }])
```
- SVG 0 bytes → retry once → log `SVG_EXPORT_FELL_BACK_TO_PNG: <name>`, export PNG.
- Image 0 bytes → retry `scale: 1` → log `ASSET_EXPORT_FAILED: <name>`, continue.
- New sub-folder in `pubspec.yaml`? Show exact diff, ask before editing.

---

## STEP 4 — Find Dart File Paths
Read `figma_config.json → project_sources.asset` for dart file paths.  
If not set → `find lib/ -name "app_svgs.dart" -o -name "app_images.dart"` → ask if not found → save into config.

---

## STEP 5 — Define Constants in Dart
Read `.claude/rules/token-naming-rules.md` **§B** (B3 icons, B4 images). Insert before closing `}`:

```dart
static const icWind = 'assets/vectors/ic_wind.svg'; // ICO_weatherWind
static const weatherHouse3d = 'assets/images/weather/house_3d.png'; // AST_weatherHouse3d
```

- Insert into existing `AppSVGs`/`AppImages` — **never create a new class**
- Append new rows to `.ui-workspace/exist_design/assets.md`: `| ICO_weatherWind | assets/vectors/ic_wind.svg | SVG | Screen |`
- **[first-time only]** Ask: *Proceed automatically in future? (Y/N)* → if Y, set `is_first_time_confirmed: true` in config.

---

## MODE B — Screen Asset Export
Called as `get-asset-figma feature=$FEATURE node_id=$NODE_ID` by `organize-figma` Phase 2c.

**B1** Read `normalize_design_code/figma_normalized.json` → collect IMAGE nodes (RECTANGLE/image-fill, `bg_`/`photo_`/`illustration_`) and SVG nodes (`VECTOR`/`COMPONENT`, `ic_`/`Icon`/`symbol`) → build `IMAGE_NODES` + `SVG_NODES` lists.

**B2** Export PNG: `save_screenshots(format:"PNG", scale:2)` → verify → retry `scale:1` on 0 bytes → log `ASSET_EXPORT_FAILED`.

**B3** Export SVG: `save_screenshots(format:"SVG")` → verify → retry once → log `SVG_EXPORT_FELL_BACK_TO_PNG`, export PNG.

**B4** Check pubspec: `grep "assets/images/\|assets/vectors/" pubspec.yaml` → append missing dirs under `flutter: > assets:`.

**B5** Write `.ui-workspace/$FEATURE/figma_asset/mapping.json`:
```json
{ "images": [{ "nodeId": "...", "file": "assets/images/bg.png", "status": "exported" }],
  "icons":  [{ "nodeId": "...", "file": "assets/vectors/ic.svg",  "status": "exported" }] }
```
Report: `get-asset-figma [MODE B] — $FEATURE: N images, M icons → mapping.json ✓`

---

## Error Handling
| Situation | Action |
|-----------|--------|
| No asset source | Stop — show instructions |
| Figma MCP not connected | Abort — reconnect instructions |
| Frame returns no nodes | Ask user to verify the frame/screen node-id passed in |
| All assets existing | Report "nothing new" and end |
| SVG export 0 bytes | Retry → fall back PNG, log `SVG_EXPORT_FELL_BACK_TO_PNG` |
| New pubspec sub-folder | Show diff, ask before editing |
| Ambiguous node | Ask user per node |

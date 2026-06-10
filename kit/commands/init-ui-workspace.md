# init-ui-workspace — UI Pipeline Project Configuration

Configures the Figma → Flutter pipeline **for this specific project**: verifies the MCP
connection, discovers where the project stores its design tokens (`project_sources`),
populates the design registries, and sets the Figma file id.

Invoke directly with `/init-ui-workspace`. Run once per project clone, after the kit files
are installed. This is a **command** — it is NOT part of the automated `organize-figma` run.

> **Prerequisite:** the pipeline files must already be installed (`bash install.sh`).
> This command does the **AI-only** part that an install script cannot: live MCP check,
> project-layout discovery (needs reading + classifying your code), and the Figma file id.
> The folder scaffold, templates and `figma_config.json` skeleton are created by `install.sh`.

---

## GUARD — Workspace must already exist

```bash
test -d .ui-workspace && test -f .ui-workspace/figma_config.json && echo OK || echo MISSING
```

If it prints `MISSING` → STOP and tell the user:
```
✗ .ui-workspace/ not set up yet.
  Run the installer first:  bash install.sh
  Then re-run /init-ui-workspace.
```
Do NOT scaffold folders here — that is the installer's job. Only proceed when the guard prints `OK`.

---

## PHASE 0 — Pre-flight: Verify figma-mcp-go Connection

Call `get_metadata` (no arguments) via figma-mcp-go:

```
mcp__figma-mcp-go__get_metadata()
```

**If the call succeeds** → print:
```
✓ figma-mcp-go connected. Configuring project…
```

**If the call fails / times out / returns an error** → STOP immediately:
```
✗ figma-mcp-go is not connected.

To connect:
  1. Open Figma Desktop → Plugins → figma-mcp-go → Start Server
  2. In Claude Code settings, add MCP server: figma-mcp-go (see .mcp.json template shipped by the kit)
  3. Re-run /init-ui-workspace after connecting.

Aborting setup.
```
Do NOT proceed past Phase 0 if the connection check fails.

---

## PHASE 1 — Discover Project Design Storage (`project_sources`)

This phase discovers WHERE the project stores its colors, fonts, assets, and widgets, then
writes those paths into `.ui-workspace/figma_config.json → project_sources` (the installer
shipped a template with common defaults — confirm or correct them here).

### 1a — Auto-scan

Run in parallel:

```bash
# Colors
find lib/ -name "app_colors.dart" -o -name "colors.dart" -o -name "app_theme.dart" | head -5
# Widgets (public)
find lib/widgets/ lib/shared/widgets/ lib/core/widgets/ -name "*.dart" 2>/dev/null | head -10
# Widgets (private — inside features)
find lib/features/ lib/pages/ -type d -name "widgets" 2>/dev/null | head -10
# Fonts
grep -rn "fontFamily\|GoogleFonts\." lib/ --include="*.dart" | head -10
# Assets
grep -A 20 "^  assets:" pubspec.yaml | head -20
find assets/ -type f 2>/dev/null | head -20
```

### 1b — Assess & Ask

| If scan found... | Action |
|-----------------|--------|
| `app_colors.dart` or `colors.dart` | Record path, no question needed |
| No color file at all | Ask: *"I couldn't find a color file. Where are your app colors defined? Send the path or type 'none'."* |
| Widgets in `lib/shared/widgets/` | Record as public widget root |
| No shared widget folder | Ask: *"Where are your shared/reusable widgets stored? Send the folder path or type 'none'."* |
| Font declared in `pubspec.yaml` | Record font family |
| Only `GoogleFonts` usage found | Note: GoogleFonts, no local font files |
| No font evidence | Ask: *"What font does this project use? Name or path in pubspec.yaml."* |
| `assets/` folder found | Record structure |
| No assets folder | Ask: *"Where are image and icon assets stored? Path in pubspec.yaml or type 'none'."* |

Ask all pending questions in a single message grouped by type — never ask one by one.

### 1c — Write `project_sources` into figma_config.json

Update `.ui-workspace/figma_config.json → project_sources` with the real paths found above
(color `dart_files` + `classes`, font `dart_files` + `font_family` + `pubspec`, asset
`svg`/`image` `dart_file` + `dir` + `class`). Replace the template placeholders. Keep
`enable_html_visualization` and `figma_file_id` untouched.

### 1d — Run get-exist-design ⚠ MANDATORY GATE

> **HARD RULE:** Phase 1d MUST complete before Phase 2 begins.
> Even if the user provided Figma links in the original command,
> store those links in memory and run get-exist-design FIRST.

After gathering paths (from scan + user answers), invoke the command:
```
/get-exist-design
```
This populates `exist_design/` with actual project widgets + assets. Wait for it to finish and
confirm the 2 registries (`widgets.md`, `assets.md`) are written before moving on. (Colors/fonts
have no registry — they are grepped from `project_sources` dart files at plan time.)

```bash
ls -lh .ui-workspace/exist_design/
grep -c "." .ui-workspace/exist_design/widgets.md
```

Only proceed to Phase 2 once `exist_design/` is confirmed populated.

---

## PHASE 2 — Set Figma file id

`.ui-workspace/figma_config.json` needs `figma_file_id` (the source Figma file).

**Step 1 — Check config:**
```bash
cat .ui-workspace/figma_config.json
```

**Step 2 — If `figma_file_id` is empty / a placeholder** → ask the user once:

```
Set figma_file_id in .ui-workspace/figma_config.json
(from the Figma URL: /design/<FILE_ID>/).
```

Wait for the user to fill it, then re-read and proceed.

> Tokens: no frame-based fetch. Colors and fonts are resolved directly by `/make-ui-plan`
> grepping the `project_sources` dart files. Assets are extracted on demand by
> `/get-asset-figma` from a screen/frame node link, or automatically during `/organize-figma`.

---

## PHASE 3 — Summary

```
╔══════════════════════════════════════════════════════╗
║        init-ui-workspace — Project Configured        ║
╠══════════════════════════════════════════════════════╣
║ MCP            figma-mcp-go connected           ✓    ║
║ project_sources written to figma_config.json    ✓    ║
║ Project scan   get-exist-design → widgets+assets ✓   ║
║ figma_file_id  set                               ✓   ║
╚══════════════════════════════════════════════════════╝

Next steps:
  • /organize-figma <figma-url>  — convert a screen to Flutter code
  • /get-exist-design            — re-scan after adding new widgets/colors
```

---

## Error Handling

| Situation | Response |
|-----------|----------|
| `.ui-workspace/` missing | Tell user to run `bash install.sh` first (see GUARD), then re-run |
| figma-mcp-go disconnects mid-run | Pause, show reconnect instructions, offer to retry from current phase |
| User sends invalid Figma URL | Ask to paste the full URL including `node-id=` parameter |
| `get-exist-design` finds nothing | Ask user to confirm project structure before continuing |

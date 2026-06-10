#!/usr/bin/env bash
# ============================================================
# install.sh — Figma→Flutter Pipeline Installer
# ============================================================
# Usage:
#   Local:  ./install.sh [/path/to/flutter-project]
#   Remote: curl -sSL https://raw.githubusercontent.com/chientran28/figma-claude-workflow/main/install.sh | bash
#
# What it does:
#   1. Detects Flutter project root (via pubspec.yaml)
#   2. Backs up existing .claude/ if present
#   3. Copies kit/ → .claude/ (always overwrites — safe to re-run for upgrades)
#   4. Merges hooks + permissions into .claude/settings.json (non-destructive)
#   5. Scaffolds .ui-workspace/ with template files (never overwrites existing)
#   6. Adds .gitignore rules for heavy pipeline artifacts
# ============================================================
set -euo pipefail

PIPELINE_VERSION="1.0.0"
REPO_URL="https://github.com/chientran28/figma-claude-workflow"
RAW_URL="https://raw.githubusercontent.com/chientran28/figma-claude-workflow/main"

# ── Colors ───────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'; BLU='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLU}→${NC} $*"; }
success() { echo -e "${GRN}✓${NC} $*"; }
warn()    { echo -e "${YLW}⚠${NC} $*"; }
error()   { echo -e "${RED}✗${NC} $*" >&2; exit 1; }

# ── 1. Detect project root ───────────────────────────────────
detect_root() {
  local arg="${1:-}"
  if [ -n "$arg" ] && [ -d "$arg" ]; then
    echo "$(cd "$arg" && pwd)"; return
  fi
  # Walk up from cwd looking for pubspec.yaml
  local d="$PWD"
  while [ "$d" != "/" ]; do
    [ -f "$d/pubspec.yaml" ] && { echo "$d"; return; }
    d="$(dirname "$d")"
  done
  echo "$PWD"
}
PROJECT_ROOT="$(detect_root "${1:-}")"
info "Project root : $PROJECT_ROOT"
[ -f "$PROJECT_ROOT/pubspec.yaml" ] || warn "pubspec.yaml not found — are you in a Flutter project?"

CLAUDE_DIR="$PROJECT_ROOT/.claude"
WS_DIR="$PROJECT_ROOT/.ui-workspace"

# ── 2. Resolve kit source (local clone vs remote tarball) ────
if [ -f "$(dirname "$0")/kit/skills/organize-figma/SKILL.md" ]; then
  # Running from a local clone
  SRC="$(cd "$(dirname "$0")" && pwd)"
  info "Source       : local clone at $SRC"
else
  # Downloaded via curl — fetch the tarball
  info "Source       : downloading from $REPO_URL"
  TMP_DIR="$(mktemp -d)"
  trap 'rm -rf "$TMP_DIR"' EXIT
  curl -sSL "$REPO_URL/archive/refs/heads/main.tar.gz" \
    | tar xz -C "$TMP_DIR" --strip-components=1
  SRC="$TMP_DIR"
fi

# ── 3. Backup existing .claude/ ──────────────────────────────
if [ -d "$CLAUDE_DIR" ]; then
  BK="${CLAUDE_DIR}.backup.$(date +%Y%m%d-%H%M%S)"
  info "Backing up   : $CLAUDE_DIR → $BK"
  cp -R "$CLAUDE_DIR" "$BK"
fi

# ── 4. Copy kit/ → .claude/ (overwrite — upgrade-safe) ──────
mkdir -p "$CLAUDE_DIR"
for d in skills agents commands hooks rules; do
  info "Copying      : kit/$d/"
  mkdir -p "$CLAUDE_DIR/$d"
  cp -R "$SRC/kit/$d/." "$CLAUDE_DIR/$d/"
done
chmod +x "$CLAUDE_DIR/hooks/"*.sh
success "kit/ installed into $CLAUDE_DIR"

# ── 5. Merge settings.json (hooks + permissions) ─────────────
merge_settings() {
  local base="$1" fragment="$2" out="$3"
  if ! command -v jq >/dev/null 2>&1; then
    warn "jq not found — skipping settings merge. Install jq and re-run install.sh."
    return
  fi

  # Deep-merge hooks arrays (concat + dedupe — idempotent on re-run/upgrade)
  jq -s '
    .[0] as $base | .[1] as $frag |
    $base
    | .hooks = (
        ($base.hooks // {}) |
        to_entries |
        . + (($frag.hooks // {}) | to_entries) |
        group_by(.key) |
        map({ key: .[0].key, value: ([ .[].value ] | add | unique) }) |
        from_entries
      )
    | .permissions.allow = (
        (($base.permissions.allow // []) + ($frag.permissions.allow // [])) | unique
      )
  ' "$base" "$fragment" > "$out"
}

SETTINGS="$CLAUDE_DIR/settings.json"
HOOKS_FRAG="$SRC/templates/settings.fragment.json"
PERM_FRAG="$SRC/templates/permissions.fragment.json"

if command -v jq >/dev/null 2>&1; then
  COMBINED="$(mktemp)"
  # Merge hooks + permissions fragments into one
  jq -s '.[0] * .[1]' "$HOOKS_FRAG" "$PERM_FRAG" > "$COMBINED"

  if [ -f "$SETTINGS" ]; then
    OUT="$(mktemp)"
    merge_settings "$SETTINGS" "$COMBINED" "$OUT"
    mv "$OUT" "$SETTINGS"
    success "Merged       : hooks + permissions into settings.json"
  else
    cp "$COMBINED" "$SETTINGS"
    success "Created      : settings.json"
  fi
  rm -f "$COMBINED"
else
  if [ ! -f "$SETTINGS" ]; then
    cp "$HOOKS_FRAG" "$SETTINGS"
    warn "Created settings.json from hooks fragment only (install jq for full merge)"
  fi
fi

# ── 6. .mcp.json — add figma-mcp-go server ───────────────────
MCP="$PROJECT_ROOT/.mcp.json"
MCP_FRAG="$SRC/templates/mcp.template.json"
if command -v jq >/dev/null 2>&1; then
  if [ -f "$MCP" ]; then
    jq -s '.[0].mcpServers = ((.[0].mcpServers // {}) * .[1].mcpServers) | .[0]' \
      "$MCP" "$MCP_FRAG" > "$MCP.tmp" && mv "$MCP.tmp" "$MCP"
    success "Merged       : figma-mcp-go into .mcp.json"
  else
    cp "$MCP_FRAG" "$MCP"
    success "Created      : .mcp.json"
  fi
else
  [ -f "$MCP" ] || cp "$MCP_FRAG" "$MCP"
  warn ".mcp.json: manual review needed (jq missing)"
fi

# ── 7. Scaffold .ui-workspace/ (cp_if_absent — never overwrite) ─
cp_if_absent() {
  local src="$1" dst="$2"
  if [ ! -f "$dst" ]; then
    cp "$src" "$dst"
    info "  Created    : $(basename "$dst")"
  fi
}

mkdir -p "$WS_DIR/exist_design"
info "Scaffolding  : .ui-workspace/"
cp_if_absent "$SRC/templates/figma_config.template.json" "$WS_DIR/figma_config.json"
cp_if_absent "$SRC/templates/token_map.template.json"    "$WS_DIR/token_map.json"
for f in flutter_helper_design.md ui_failed.md learnings.md learnings_archive.md; do
  cp_if_absent "$SRC/templates/ui-workspace/$f" "$WS_DIR/$f"
done
[ -d "$WS_DIR/exist_design" ] || mkdir -p "$WS_DIR/exist_design"

# ── 8. Record pipeline version ───────────────────────────────
echo "$PIPELINE_VERSION" > "$CLAUDE_DIR/.figma-pipeline-version"

# ── 9. .gitignore rules ───────────────────────────────────────
GI="$PROJECT_ROOT/.gitignore"
if [ -f "$GI" ] && ! grep -q "figma-to-flutter pipeline" "$GI" 2>/dev/null; then
  cat >> "$GI" <<'GITIGNORE'

# figma-to-flutter pipeline — heavy artifacts (do not commit)
.ui-workspace/*/figma_widget/
.ui-workspace/*/figma_fullscreen/
.ui-workspace/*/figma_code/
.ui-workspace/*/normalize_design_code/
.ui-workspace/*/figma_asset/
.ui-workspace/*/preview.html
.ui-workspace/*/pipeline.md
.claude.backup.*/
GITIGNORE
  success "Updated      : .gitignore"
elif [ ! -f "$GI" ]; then
  cat > "$GI" <<'GITIGNORE'
# figma-to-flutter pipeline — heavy artifacts (do not commit)
.ui-workspace/*/figma_widget/
.ui-workspace/*/figma_fullscreen/
.ui-workspace/*/figma_code/
.ui-workspace/*/normalize_design_code/
.ui-workspace/*/figma_asset/
.ui-workspace/*/preview.html
.ui-workspace/*/pipeline.md
.claude.backup.*/
GITIGNORE
  success "Created      : .gitignore"
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${GRN}══════════════════════════════════════════════════════${NC}"
echo -e "${GRN}  Figma→Flutter Pipeline v${PIPELINE_VERSION} installed!${NC}"
echo -e "${GRN}══════════════════════════════════════════════════════${NC}"
echo ""
echo "Next steps (required — AI does these, not this script):"
echo ""
echo "  1. Open Figma Desktop → Plugins → figma-mcp-go → Start Server"
echo ""
echo "  2. Open Claude Code in your project, then run:"
echo "       /init-ui-workspace"
echo "     (auto-scans project_sources, sets figma_file_id, builds token_map.json)"
echo ""
echo "  3. Convert your first screen:"
echo "       /organize-figma <figma-node-url>"
echo ""
echo "  Docs: $REPO_URL"
echo ""

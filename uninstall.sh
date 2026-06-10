#!/usr/bin/env bash
# ============================================================
# uninstall.sh — Figma→Flutter Pipeline Uninstaller
# ============================================================
# Usage:
#   ./uninstall.sh [/path/to/flutter-project] [--purge]
#
#   --purge  Also delete .ui-workspace/ (WARNING: destroys accumulated
#            knowledge — flutter_helper_design.md, ui_failed.md, learnings.md)
#
# Without --purge: removes pipeline skills/agents/commands/hooks/rules and
# cleans their hooks from settings.json. Keeps .ui-workspace/ intact.
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[0;33m'; BLU='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLU}→${NC} $*"; }
success() { echo -e "${GRN}✓${NC} $*"; }
warn()    { echo -e "${YLW}⚠${NC} $*"; }

# ── Args ─────────────────────────────────────────────────────
PROJECT_ROOT="${1:-$PWD}"
[ -d "$PROJECT_ROOT" ] || { echo "Not a directory: $PROJECT_ROOT" >&2; exit 1; }
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
PURGE=false
for arg in "$@"; do [ "$arg" = "--purge" ] && PURGE=true; done

CLAUDE_DIR="$PROJECT_ROOT/.claude"
WS_DIR="$PROJECT_ROOT/.ui-workspace"

echo ""
echo -e "${RED}Figma→Flutter Pipeline Uninstaller${NC}"
info "Project: $PROJECT_ROOT"
$PURGE && warn "--purge: will also delete .ui-workspace/ (all accumulated knowledge)"
echo ""

# ── Pipeline-owned files (exactly what install.sh places) ────
PIPELINE_SKILLS="organize-figma analyze-design make-ui-plan coding-ui learn-from-failed"
PIPELINE_AGENTS="figma-extract-agent analyze-design-agent ui-plan-architect ui-code-agent"
PIPELINE_CMDS="normalize-figma-file init-ui-workspace get-asset-figma get-exist-design skeleton"
PIPELINE_HOOKS="dart-analyze-feedback knowledge-eval known-patterns-inject learnings-reinjection pipeline-gate"
PIPELINE_RULES="token-naming-rules coding-standards clean-code-scalability l10n-reuse"

# Skills
info "Removing skills..."
for s in $PIPELINE_SKILLS; do
  [ -d "$CLAUDE_DIR/skills/$s" ] && rm -rf "$CLAUDE_DIR/skills/$s" && echo "  - $s"
done

# Agents
info "Removing agents..."
for a in $PIPELINE_AGENTS; do
  [ -f "$CLAUDE_DIR/agents/$a.md" ] && rm -f "$CLAUDE_DIR/agents/$a.md" && echo "  - $a"
done

# Commands
info "Removing commands..."
for c in $PIPELINE_CMDS; do
  [ -f "$CLAUDE_DIR/commands/$c.md" ] && rm -f "$CLAUDE_DIR/commands/$c.md" && echo "  - $c"
done
# Only remove our script — user may keep their own files in commands/scripts/
[ -f "$CLAUDE_DIR/commands/scripts/figma_preprocessor.py" ] \
  && rm -f "$CLAUDE_DIR/commands/scripts/figma_preprocessor.py" \
  && echo "  - commands/scripts/figma_preprocessor.py"
rmdir "$CLAUDE_DIR/commands/scripts" 2>/dev/null || true

# Hooks
info "Removing hooks..."
for h in $PIPELINE_HOOKS; do
  [ -f "$CLAUDE_DIR/hooks/$h.sh" ] && rm -f "$CLAUDE_DIR/hooks/$h.sh" && echo "  - $h.sh"
done

# Rules
info "Removing rules..."
for r in $PIPELINE_RULES; do
  [ -f "$CLAUDE_DIR/rules/$r.md" ] && rm -f "$CLAUDE_DIR/rules/$r.md" && echo "  - $r"
done

# Version marker
rm -f "$CLAUDE_DIR/.figma-pipeline-version"

# ── Clean pipeline hooks from settings.json ──────────────────
SETTINGS="$CLAUDE_DIR/settings.json"
if command -v jq >/dev/null 2>&1 && [ -f "$SETTINGS" ]; then
  info "Cleaning pipeline hooks from settings.json..."
  HOOK_PATTERN="dart-analyze-feedback|knowledge-eval|known-patterns-inject|learnings-reinjection|pipeline-gate"
  jq --arg pat "$HOOK_PATTERN" '
    .hooks |= (
      if . == null then null
      else
        with_entries(
          .value |= (
            map(.hooks |= map(select(.command | test($pat) | not)))
            | map(select(.hooks | length > 0))
          )
        )
        | with_entries(select(.value | length > 0))
      end
    )
  ' "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS"
  success "Cleaned pipeline hooks from settings.json (other hooks preserved)"
else
  warn "jq not found or settings.json missing — clean hooks manually if needed"
fi

# ── Workspace ─────────────────────────────────────────────────
if $PURGE; then
  if [ -d "$WS_DIR" ]; then
    warn "Deleting .ui-workspace/ (all accumulated knowledge will be lost)"
    rm -rf "$WS_DIR"
    success "Deleted $WS_DIR"
  fi
else
  info ".ui-workspace/ kept intact (use --purge to also remove it)"
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
success "Pipeline uninstalled from $PROJECT_ROOT"
echo "  Note: any .claude.backup.* directories from install were not removed."
echo ""

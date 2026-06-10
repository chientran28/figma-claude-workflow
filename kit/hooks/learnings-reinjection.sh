#!/bin/bash
# learnings-reinjection.sh
# Trigger: PostCompact
# After context compaction, re-inject summary of UI knowledge base so Claude doesn't lose context.

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

UI_FAILED="$CWD/.ui-workspace/ui_failed.md"
HELPER="$CWD/.ui-workspace/flutter_helper_design.md"

PATTERN_COUNT=$(grep -c "^| UI-" "$UI_FAILED" 2>/dev/null || echo 0)
SECTION_COUNT=$(grep -c "^## " "$HELPER" 2>/dev/null || echo 0)

echo "📚 [context-restored] UI Knowledge Base: $PATTERN_COUNT known error patterns, $SECTION_COUNT fix sections in flutter_helper_design.md"
echo "Auto-checks: gradient+opacity→UI-GRADIENT-*, inner shadow→UI-SHADOW-*, Column no scroll→UI-SCROLL-*, Text in Row→UI-OVERFLOW-*"
echo "Use /learn-from-failed to add new patterns."

exit 0

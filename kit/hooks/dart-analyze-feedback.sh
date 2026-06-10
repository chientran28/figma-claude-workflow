#!/bin/bash
# dart-analyze-feedback.sh
# Trigger: PostToolUse(Edit|Write)
# After Claude edits a .dart file, auto-run dart analyze and inject known UI patterns if errors found.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

# Only process .dart files
[[ "$FILE_PATH" != *.dart ]] && exit 0

# Run dart analyze on the edited file
RESULT=$(dart analyze "$FILE_PATH" 2>&1)

# If UI render / overflow errors detected → inject known patterns as context
if echo "$RESULT" | grep -qiE "overflow|renderflex|unbounded|render|layout"; then
  UI_FAILED="$CWD/.ui-workspace/ui_failed.md"
  if [ -f "$UI_FAILED" ]; then
    echo "📚 [dart-analyze] UI render/overflow error detected. Known related patterns:"
    grep -iE "overflow|scroll|column|row|expanded" "$UI_FAILED" | grep "^| UI-" | head -4
    echo ""
  fi
fi

# Show errors/warnings if any
if echo "$RESULT" | grep -qE "^.*error"; then
  echo "[dart-analyze] $FILE_PATH:"
  echo "$RESULT" | grep -E "error|warning" | head -10
fi

exit 0

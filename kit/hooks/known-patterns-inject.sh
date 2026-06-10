#!/bin/bash
# known-patterns-inject.sh
# Trigger: UserPromptSubmit
# When user describes a UI bug, inject known patterns from ui_failed.md as context.

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | jq -r '.prompt // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

# Skip empty/whitespace prompts.
if [ -z "$(echo "$PROMPT" | tr -d '[:space:]')" ]; then
  exit 0
fi

# Skip setup / non-bug slash commands — they never need UI failure hints.
if echo "$PROMPT" | grep -qE \
  "^/(init-ui-workspace|get-exist-design|organize-figma|normalize-figma-file|make-ui-plan|get-(color|font|asset)-figma|analyze-design|coding-ui)\b"; then
  exit 0
fi

# Keyword check — English + Vietnamese UI-related terms
if ! echo "$PROMPT" | grep -qiE \
  "overflow|layout|gradient|shadow|scroll|anim|color|image|component|render|widget|\
lỗi|fix|broken|wrong|learn.from|lint|text overflow|padding|border|blur|opacity|UI"; then
  exit 0
fi

UI_FAILED="$CWD/.ui-workspace/ui_failed.md"
[ ! -f "$UI_FAILED" ] && exit 0

# Match each keyword → find relevant rows
RELEVANT=""
for kw in overflow layout gradient shadow scroll animation color text image component blur opacity; do
  if echo "$PROMPT" | grep -qi "$kw"; then
    ROWS=$(grep -i "$kw" "$UI_FAILED" | grep "^| UI-" | head -2)
    [ -n "$ROWS" ] && RELEVANT="${RELEVANT}
${ROWS}"
  fi
done

if [ -n "$RELEVANT" ]; then
  echo "📚 Known UI patterns that may apply:"
  echo "$RELEVANT" | sort -u | grep -v "^$" | head -6
  echo "→ Full details: .ui-workspace/flutter_helper_design.md"
  echo ""
fi

exit 0

#!/bin/bash
# knowledge-eval.sh
# Trigger: PostToolUse(Write)
# After skill writes to a knowledge file, validate file health and run archival.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')

# Only process knowledge files
case "$FILE_PATH" in
  *flutter_helper_design.md|*ui_failed.md|*learnings.md) ;;
  *) exit 0 ;;
esac

LINE_COUNT=$(wc -l < "$FILE_PATH" 2>/dev/null | tr -d ' ' || echo 0)

# Bloat warning
if [ "$LINE_COUNT" -gt 500 ]; then
  echo "⚠️ [knowledge-eval] $FILE_PATH: $LINE_COUNT lines — consider curation (merge similar entries, remove duplicates)"
fi

# Validate ui_failed.md ----------------------------------------------------
if [[ "$FILE_PATH" == *ui_failed.md ]]; then
  DUPES=$(grep -oE 'UI-[A-Z]+-[0-9]+' "$FILE_PATH" | sort | uniq -d)
  if [ -n "$DUPES" ]; then
    echo "⚠️ [knowledge-eval] Duplicate error codes found: $DUPES — merge these entries"
  else
    COUNT=$(grep -c "^| UI-" "$FILE_PATH" 2>/dev/null || echo 0)
    echo "✓ [knowledge-eval] ui_failed.md: $COUNT patterns, no duplicates ($LINE_COUNT lines)"
  fi

  # Dead-link check: every #ui-… anchor referenced must exist as {#ui-…} in flutter_helper_design.md
  HELPER="$CWD/.ui-workspace/flutter_helper_design.md"
  if [ -f "$HELPER" ]; then
    DEAD=""
    for anchor in $(grep -oE '#ui-[a-z0-9-]+' "$FILE_PATH" | sort -u); do
      if ! grep -qE "\{$anchor\}" "$HELPER"; then
        DEAD="${DEAD}${anchor} "
      fi
    done
    if [ -n "$DEAD" ]; then
      echo "⚠️ [knowledge-eval] DEAD LINK(s) in ui_failed.md — not found in flutter_helper_design.md: $DEAD"
    fi
  fi
fi

# Validate flutter_helper_design.md ----------------------------------------
if [[ "$FILE_PATH" == *flutter_helper_design.md ]]; then
  SECTION_COUNT=$(grep -c "^## " "$FILE_PATH" 2>/dev/null || echo 0)
  echo "✓ [knowledge-eval] flutter_helper_design.md: $SECTION_COUNT sections, $LINE_COUNT lines"

  # Re-check ui_failed.md links against this file (only flag orphan anchors HERE that nothing references — informational).
  UI_FAILED="$CWD/.ui-workspace/ui_failed.md"
  if [ -f "$UI_FAILED" ]; then
    DEAD=""
    for anchor in $(grep -oE '#ui-[a-z0-9-]+' "$UI_FAILED" | sort -u); do
      if ! grep -qE "\{$anchor\}" "$FILE_PATH"; then
        DEAD="${DEAD}${anchor} "
      fi
    done
    if [ -n "$DEAD" ]; then
      echo "⚠️ [knowledge-eval] ui_failed.md references missing anchors here: $DEAD"
    fi
  fi
fi

# Archival for learnings.md ------------------------------------------------
# Move entries older than 30 days from learnings.md → learnings_archive.md.
if [[ "$FILE_PATH" == *learnings.md && "$FILE_PATH" != *learnings_archive.md ]]; then
  ARCHIVE="$CWD/.ui-workspace/learnings_archive.md"
  [ ! -f "$ARCHIVE" ] && exit 0

  CUTOFF=$(date -v-30d +%Y-%m-%d 2>/dev/null || date -d "-30 days" +%Y-%m-%d 2>/dev/null)
  [ -z "$CUTOFF" ] && exit 0

  # Find lines that look like: [CATEGORY] YYYY-MM-DD: ...
  OLD_LINES=$(grep -E '^\[[A-Z_]+\] [0-9]{4}-[0-9]{2}-[0-9]{2}:' "$FILE_PATH" \
              | awk -v cutoff="$CUTOFF" '{
                  # date is field 2 in form YYYY-MM-DD
                  d = $2; sub(":$", "", d);
                  if (d < cutoff) print $0;
                }')

  if [ -n "$OLD_LINES" ]; then
    COUNT=$(echo "$OLD_LINES" | wc -l | tr -d ' ')
    {
      echo ""
      echo "<!-- archived on $(date +%Y-%m-%d) -->"
      echo "$OLD_LINES"
    } >> "$ARCHIVE"

    # Remove those lines from the active file (BSD/macOS-safe with .bak then delete).
    TMP=$(mktemp)
    awk -v cutoff="$CUTOFF" '
      /^\[[A-Z_]+\] [0-9]{4}-[0-9]{2}-[0-9]{2}:/ {
        d = $2; sub(":$", "", d);
        if (d < cutoff) next;
      }
      { print }
    ' "$FILE_PATH" > "$TMP" && mv "$TMP" "$FILE_PATH"

    echo "✓ [knowledge-eval] Archived $COUNT learnings entries older than $CUTOFF → learnings_archive.md"
  fi
fi

exit 0

#!/bin/bash
# pipeline-gate.sh
# Trigger: Stop
# Blocks "done" while an ACTIVE organize-figma run is incomplete — i.e. the most recently touched
# .ui-workspace/<feature>/plan/plan.md is still `Status: IN_PROGRESS`. The pipeline now ENDS at
# coding: once every `## Widget Phase` row is DONE and the final `flutter analyze` is clean, the
# coordinator flips Status to DONE — that flip is the only completion signal the hook enforces
# (there is no score/verify step anymore). Tightly scoped so it never blocks unrelated sessions:
#   - loop guard (stop_hook_active)
#   - only the newest plan.md, only if modified in the last 30 min
#   - only if Status: IN_PROGRESS
# Emits {"decision":"block","reason":...} to push the model back to the unfinished step.

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')

# Loop guard: if we already blocked once and the model is continuing, do not re-block.
[ "$STOP_ACTIVE" = "true" ] && exit 0

# Newest plan.md (ls -t = newest first).
PLAN=$(ls -t "$CWD"/.ui-workspace/*/plan/plan.md 2>/dev/null | head -1)
[ -z "$PLAN" ] && exit 0
[ ! -f "$PLAN" ] && exit 0

# Freshness: only act on a plan touched in the last 30 min (1800s). Portable mtime.
MTIME=$(stat -f %m "$PLAN" 2>/dev/null || stat -c %Y "$PLAN" 2>/dev/null)
NOW=$(date +%s)
[ -z "$MTIME" ] && exit 0
[ $(( NOW - MTIME )) -gt 1800 ] && exit 0

# Only gate runs still IN_PROGRESS. Status: DONE → allow stop.
grep -qE '^##[[:space:]]*Status:[[:space:]]*IN_PROGRESS' "$PLAN" || exit 0

# Count Widget Phase rows whose last cell is still pending (TODO / Reuse / New).
# Complete cells: "DONE", "DONE (NEW)", "DONE (REUSE)", … (any DONE prefix) and "SKIP"
# (rows intentionally never coded — e.g. spacers, OS home indicator).
PENDING=$(awk '
  /^##[[:space:]]*Widget Phase/ { f=1; next }
  f && /^##[[:space:]]/         { f=0 }
  f && /^\|/ {
    if ($0 ~ /Phase[[:space:]]*\|/) next            # header row
    if ($0 ~ /^\|[[:space:]]*-/)    next            # separator row
    n = split($0, a, "|"); cell = a[n-1]
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", cell)
    if (cell !~ /^DONE/ && cell != "SKIP" && cell != "") print cell
  }' "$PLAN" | grep -c .)

FEATURE=$(basename "$(dirname "$(dirname "$PLAN")")")
if [ "$PENDING" -gt 0 ]; then
  REASON="Pipeline incomplete for '$FEATURE': $PENDING Widget Phase row(s) not DONE. Resume organize-figma Step 4 (code each remaining row, then 'flutter analyze' clean), or set Status: DONE if intentionally stopping. See $PLAN."
else
  REASON="Pipeline incomplete for '$FEATURE': all Widget Phase rows are DONE/SKIP but Status is still IN_PROGRESS. Run the final 'flutter analyze' and set ## Status: DONE in $PLAN, or set it now if intentionally stopping."
fi

jq -n --arg r "$REASON" '{decision:"block", reason:$r}'
exit 0

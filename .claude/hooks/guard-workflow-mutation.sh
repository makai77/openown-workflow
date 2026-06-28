#!/usr/bin/env bash
# The most important hook for this project: hard-blocks a direct `.status =`
# assignment anywhere in applications/ outside the workflow service itself,
# BEFORE the edit lands. This is the one architectural rule that must not be
# left to good intentions.
set -euo pipefail
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
NEW_CONTENT=$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // ""')

if [[ "$FILE_PATH" == *"/applications/"* ]] \
  && [[ "$FILE_PATH" != *"services/workflow.py" ]] \
  && [[ "$FILE_PATH" != *"/models.py" ]] \
  && [[ "$FILE_PATH" != *"/migrations/"* ]] \
  && [[ "$FILE_PATH" != *"/tests/"* ]] \
  && echo "$NEW_CONTENT" | grep -qE '\.status[[:space:]]*=[^=]'; then
  echo "Blocked: direct '.status =' assignment outside services/workflow.py in $FILE_PATH. Use the existing service function (submit_application / start_review_application / approve_application / reject_application / return_application) instead." >&2
  exit 2
fi
exit 0

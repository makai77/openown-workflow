#!/usr/bin/env bash
# Deliberately NOT a hard block — hand-editing a migration is sometimes correct
# (data migrations, squashing). Allows the edit but injects a reminder Claude sees.
set -euo pipefail
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [[ "$FILE_PATH" == *"/migrations/"*.py ]]; then
  echo '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "additionalContext": "Editing a migration file directly. Prefer makemigrations for schema changes; hand-edit only for data migrations or squashing, and run makemigrations --check afterward."}}'
fi
exit 0

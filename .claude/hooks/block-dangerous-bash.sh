#!/usr/bin/env bash
# Hard-blocks destructive shell commands before they run.
# exit 2 = block the tool call and feed the message back to Claude as the reason.
set -euo pipefail
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

if echo "$COMMAND" | grep -qiE \
  'rm[[:space:]]+-rf|git[[:space:]]+reset[[:space:]]+--hard|git[[:space:]]+clean[[:space:]]+-fd|docker[[:space:]]+compose[[:space:]].*down[[:space:]].*-v|dropdb|DROP[[:space:]]+DATABASE|TRUNCATE|DELETE[[:space:]]+FROM[[:space:]]+applications_'; then
  echo "Blocked: '$COMMAND' matches a destructive command pattern. If this is genuinely intended, run it manually outside Claude Code." >&2
  exit 2
fi
exit 0

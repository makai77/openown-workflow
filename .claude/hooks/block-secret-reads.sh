#!/usr/bin/env bash
# Hard-blocks reads of secret files so they never enter the agent's context.
set -euo pipefail
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.pattern // ""')

if echo "$FILE_PATH" | grep -qE '(^|/)\.env($|\.)|(^|/)\.envs/\.production|(^|/)secrets/|\.pem$|\.key$'; then
  echo "Blocked: reading $FILE_PATH is not allowed by project policy. Secrets stay out of the agent's context." >&2
  exit 2
fi
exit 0

#!/usr/bin/env bash
# The one genuinely low-risk "do this automatically" hook: formatting can't
# break correctness. Runs Ruff on any Python file Claude just wrote or edited.
set -euo pipefail
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

if [[ "$FILE_PATH" == *.py ]]; then
  docker compose -f docker-compose.local.yml run --rm django ruff format "$FILE_PATH" 2>&1 || true
fi
exit 0

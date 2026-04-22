#!/usr/bin/env bash
# Reads tool_input.file_path from stdin; skips non-.py files to avoid
# running the suite on every markdown or config edit.
set -euo pipefail

FILE_PATH=$(jq -r '.tool_input.file_path // ""')

if [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

cd "$(dirname "$0")/../.."
exec .venv/bin/pytest src/tests/ -q --ignore=src/tests/test_subagents.py

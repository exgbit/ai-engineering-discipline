#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi
"$PYTHON" "$SCRIPT_DIR/execute_request.py" "$@"

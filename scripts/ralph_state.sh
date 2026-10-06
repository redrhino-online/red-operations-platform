#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
exec python3 "$SCRIPT_DIR/ralph_state.py" "${1:-prepare}" "${2:-$SCRIPT_DIR/..}"

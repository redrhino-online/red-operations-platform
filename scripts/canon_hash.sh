#!/usr/bin/env bash
# Print a stable sha256 of the reference canon content (transcripts and docs).
# Paths are hashed relative to the canon root so the value does not depend on
# where the canon lives. Used by the harness to pin and freeze the canon.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CANON_DIR="${1:-${RALPH_CANON:-$(cd "$SCRIPT_DIR/../.." && pwd -P)/canon}}"
[[ -d "$CANON_DIR" ]] || { printf 'canon dir not found: %s\n' "$CANON_DIR" >&2; exit 2; }
(
  cd "$CANON_DIR"
  find . -type f \( -name '*.txt' -o -name '*.md' \) \
    -not -path './.git/*' -not -path './.venv/*' -not -path './site/*' \
    -print0 | LC_ALL=C sort -z | xargs -0 sha256sum
) | sha256sum | awk '{print $1}'

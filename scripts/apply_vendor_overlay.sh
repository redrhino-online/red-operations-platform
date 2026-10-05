#!/usr/bin/env bash
# Apply or verify the committed RED vendor overlay (ADR 0011).
#
# The vendored OpenExecutive submodule is a pinned dependency (ADR 0008). RED
# edits it only through the overlay under vendor/overlay/, so every local vendor
# change is declared, reproducible and re-triggerable after an upstream bump.
# Re-running apply is a no-op.
#
#   scripts/apply_vendor_overlay.sh          apply the overlay onto the submodule
#   scripts/apply_vendor_overlay.sh --check  verify the tree equals the overlay
#
# The DoD gate ([4/6], SPEC.md section 13 condition 7) runs `--check`.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

action="apply"
if [[ "${1:-}" == "--check" ]]; then
  action="check"
elif [[ -n "${1:-}" && "${1:-}" != "--apply" ]]; then
  printf 'usage: %s [--check]\n' "$0" >&2
  exit 2
fi

exec uv run python scripts/vendor_overlay.py "$action"

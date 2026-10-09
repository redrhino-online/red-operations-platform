#!/usr/bin/env bash
# Verify DoD condition 8's branding and notice evidence: the Director name and
# user-facing UI copy are RED (no OpenExecutive branding), and the vendored
# dependency retains its LICENSE and NOTICE. Called by
# scripts/check_definition_of_done.sh [5/7].
#
# SPEC.md section 13 condition 8: "the Director name, agent charters and UI copy
# are RED with no OpenExecutive branding in user facing surfaces, and LICENSE and
# NOTICE are retained." Since the single-shell overhaul (SPEC.md section 14,
# ADR 0013) the cockpit is the only user-facing UI, so this scans the RED-owned
# cockpit surfaces (the shell, the native `/operations/*` screens and the shared
# workspace context) rather than the retired `/screens` thin client. The absorbed
# vendor tree legitimately carries upstream OpenExecutive references outside
# those surfaces, so the scan is scoped to the RED-owned UI copy.
#
# Usage: check_branding_and_notice.sh <ui-dir> <vendor-dir>
set -Eeuo pipefail

ui_dir="${1:?cockpit UI directory required}"
vendor_dir="${2:?vendor directory required}"

fail() { printf 'branding/notice: %s\n' "$*" >&2; exit 1; }

[[ -d "$ui_dir" ]] || fail "cockpit UI directory '$ui_dir' is missing"

for notice in LICENSE NOTICE; do
  [[ -s "$vendor_dir/$notice" ]] \
    || fail "the vendored dependency is missing a non-empty $notice"
done

# The RED-owned user-facing surfaces: the shell, the native screens and the
# shared workspace context. Only existing paths are scanned.
surfaces=(
  "$ui_dir/src/app/layout.tsx"
  "$ui_dir/src/app/operations"
  "$ui_dir/src/components/operations"
  "$ui_dir/src/components/workspace"
  "$ui_dir/src/components/shell"
)
existing=()
for surface in "${surfaces[@]}"; do
  [[ -e "$surface" ]] && existing+=("$surface")
done

if (( ${#existing[@]} > 0 )); then
  if command -v rg >/dev/null 2>&1; then
    if rg -q 'OpenExecutive' "${existing[@]}" 2>/dev/null; then
      fail "OpenExecutive branding found in the RED cockpit surfaces; user-facing copy must be RED branded"
    fi
  elif grep -rq 'OpenExecutive' "${existing[@]}" 2>/dev/null; then
    fail "OpenExecutive branding found in the RED cockpit surfaces; user-facing copy must be RED branded"
  fi
fi

grep -q 'RED Operations Director' "$ui_dir/src/app/layout.tsx" \
  || fail "the Director is not named RED in $ui_dir/src/app/layout.tsx"

printf 'branding/notice ok: RED Director name, no OpenExecutive branding, LICENSE/NOTICE retained\n'

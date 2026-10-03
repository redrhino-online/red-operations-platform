#!/usr/bin/env bash
# Verify DoD condition 8's branding and notice evidence: the Director name and
# user-facing UI copy are RED (no OpenExecutive branding), and the vendored
# dependency retains its LICENSE and NOTICE. Called by
# scripts/check_definition_of_done.sh [5/6].
#
# SPEC.md section 13 condition 8: "the Director name, agent charters and UI copy
# are RED with no OpenExecutive branding in user facing surfaces, and LICENSE and
# NOTICE are retained." The prior [5/6] inline scan covered the frontend only, so
# a missing notice could not fail the gate. This check makes the branding and the
# retained-license evidence explicit and named.
#
# Usage: check_branding_and_notice.sh <frontend-dir> <vendor-dir>
set -Eeuo pipefail

frontend_dir="${1:?frontend directory required}"
vendor_dir="${2:?vendor directory required}"

fail() { printf 'branding/notice: %s\n' "$*" >&2; exit 1; }

[[ -d "$frontend_dir" ]] || fail "frontend/ is missing"

for notice in LICENSE NOTICE; do
  [[ -s "$vendor_dir/$notice" ]] \
    || fail "the vendored dependency is missing a non-empty $notice"
done

if command -v rg >/dev/null 2>&1; then
  if rg -q 'OpenExecutive' "$frontend_dir" \
    --glob '!**/node_modules/**' --glob '!**/.next/**' 2>/dev/null; then
    fail "OpenExecutive branding found in frontend/; user-facing surfaces must be RED branded"
  fi
fi

grep -q 'RED Operations Director' "$frontend_dir/src/app/layout.tsx" \
  || fail "the Director is not named RED in frontend/src/app/layout.tsx"

printf 'branding/notice ok: RED Director name, no OpenExecutive branding, LICENSE/NOTICE retained\n'

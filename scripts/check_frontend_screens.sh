#!/usr/bin/env bash
# Verify the RED cockpit renders every SPEC.md section 8 screen as a native
# `/operations/*` page and ships a component test suite. Called by
# scripts/check_definition_of_done.sh [5/7].
#
# DoD condition 6 (SPEC.md section 13) requires "All section 8 screens render".
# Since the single-shell overhaul (SPEC.md section 14, ADR 0013) the cockpit is
# the only user-facing UI, so this gate exercises the cockpit pages, not the
# retired `/screens` thin client.
#
# The check is data-driven: the repo declares each implemented screen in a
# manifest, one `<screen-id> <route>` per line, where the route starts with
# `/operations/`. Every canonical section 8 screen id must be declared, and each
# declared route must resolve to a cockpit app-router page
# `<cockpit-ui-dir>/src/app/<route>/page.*`. A screens-less shell fails here
# rather than passing the stop gate.
#
# Usage: check_frontend_screens.sh <cockpit-ui-dir> <manifest> <test-dir>
set -Eeuo pipefail

cockpit="${1:?cockpit UI directory required}"
manifest="${2:?screen manifest required}"
test_dir="${3:?component test directory required}"

fail() { printf 'cockpit screens: %s\n' "$*" >&2; exit 1; }

[[ -d "$cockpit" ]] || fail \
  "cockpit UI directory '$cockpit' is missing; the DoD requires the RED cockpit and all section 8 screens"

required_screens=(
  portfolio-command-center
  client-workspace-overview
  source-and-claim-explorer
  transformation-map
  offer-and-journey-editor
  build-board
  approval-inbox
  workflow-run-detail
  launch-readiness
  performance-review
  portfolio-opportunities
  authority-settings
)

[[ -f "$manifest" ]] || fail \
  "missing $manifest; declare each section 8 screen as '<screen-id> /operations/<route>'"

declare -A route_of
while read -r id route _; do
  [[ -z "${id:-}" || "$id" == \#* ]] && continue
  [[ -n "${route:-}" && "$route" == /operations/* ]] || fail \
    "manifest line for '$id' needs a native route beginning with '/operations/'"
  route_of["$id"]="$route"
done < "$manifest"

missing=()
for id in "${required_screens[@]}"; do
  [[ -n "${route_of[$id]:-}" ]] || missing+=("$id")
done
(( ${#missing[@]} == 0 )) || fail \
  "section 8 screens not declared in the manifest: ${missing[*]}"

for id in "${required_screens[@]}"; do
  route="${route_of[$id]}"
  rel="${route#/}"
  compgen -G "$cockpit/src/app/$rel/page.*" >/dev/null || fail \
    "no cockpit page for screen '$id' at route '$route' (looked under $cockpit/src/app/$rel)"
done

[[ -d "$test_dir" ]] || fail \
  "component test directory '$test_dir' is missing; condition 6 requires screen tests"

spec_found=0
while IFS= read -r file; do spec_found=1; break; done < <(
  find "$test_dir" \
    \( -name node_modules -o -name .next -o -name dist \) -prune -o \
    -type f \( -name '*.spec.ts' -o -name '*.spec.tsx' -o -name '*.spec.js' \
      -o -name '*.spec.jsx' -o -name '*.test.ts' -o -name '*.test.tsx' \
      -o -name '*.test.js' -o -name '*.test.jsx' \) -print
)
(( spec_found == 1 )) || fail \
  "no component test suite found under $test_dir; condition 6 requires screen tests"

printf 'cockpit screens ok: %s section 8 screens declared with native /operations pages and a component suite\n' \
  "${#required_screens[@]}"

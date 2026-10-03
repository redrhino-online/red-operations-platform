#!/usr/bin/env bash
# Verify the RED frontend renders every SPEC.md section 8 screen and ships a
# browser test suite. Called by scripts/check_definition_of_done.sh [5/6].
#
# DoD condition 6 (SPEC.md section 13) requires "All section 8 screens render":
# the frontend builds and browser tests cover the portfolio command center,
# client workspace overview, source and claim explorer, transformation map,
# offer and journey editor, build board with dependency view, approval inbox
# with exact version diff, workflow run detail, launch readiness, performance
# review, portfolio opportunities and authority settings.
#
# The check is data-driven so a future cycle chooses its own routes: the
# frontend declares each implemented screen in `frontend/dod-screens.txt`, one
# `<screen-id> <route>` per line, where the route starts with `/`. Every
# canonical section 8 screen id must be declared, and each declared route must
# resolve to a page (Next.js app router `frontend/src/app/<route>/page.*` or
# pages router `frontend/src/pages/<route>.*`/`index.*`). A screens-less shell
# fails here rather than passing the stop gate.
#
# Usage: check_frontend_screens.sh <frontend-dir>
set -Eeuo pipefail

frontend="${1:?frontend directory required}"

fail() { printf 'frontend screens: %s\n' "$*" >&2; exit 1; }

[[ -d "$frontend" ]] || fail "frontend/ is missing; the DoD requires the RED branded UI and all section 8 screens"

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

manifest="$frontend/dod-screens.txt"
[[ -f "$manifest" ]] || fail \
  "missing $manifest; declare each section 8 screen as '<screen-id> <route>'"

declare -A route_of
while read -r id route _; do
  [[ -z "${id:-}" || "$id" == \#* ]] && continue
  [[ -n "${route:-}" && "$route" == /* ]] || fail \
    "manifest line for '$id' needs a route beginning with '/'"
  route_of["$id"]="$route"
done < "$manifest"

missing=()
for id in "${required_screens[@]}"; do
  [[ -n "${route_of[$id]:-}" ]] || missing+=("$id")
done
(( ${#missing[@]} == 0 )) || fail \
  "section 8 screens not declared in dod-screens.txt: ${missing[*]}"

has_page() {
  local route="$1" rel dir
  rel="${route#/}"
  if [[ -z "$rel" ]]; then
    dir="$frontend/src/app"
  else
    dir="$frontend/src/app/$rel"
  fi
  if compgen -G "$dir/page.*" >/dev/null; then return 0; fi
  if [[ -n "$rel" ]]; then
    if compgen -G "$frontend/src/pages/$rel.*" >/dev/null; then return 0; fi
    if compgen -G "$frontend/src/pages/$rel/index.*" >/dev/null; then return 0; fi
  else
    if compgen -G "$frontend/src/pages/index.*" >/dev/null; then return 0; fi
  fi
  return 1
}

for id in "${required_screens[@]}"; do
  route="${route_of[$id]}"
  has_page "$route" || fail \
    "no page for screen '$id' at route '$route' (looked under frontend/src/app and frontend/src/pages)"
done

spec_found=0
while IFS= read -r file; do spec_found=1; break; done < <(
  find "$frontend" \
    \( -name node_modules -o -name .next -o -name dist \) -prune -o \
    -type f \( -name '*.spec.ts' -o -name '*.spec.tsx' -o -name '*.spec.js' \
      -o -name '*.spec.jsx' -o -name '*.test.ts' -o -name '*.test.tsx' \
      -o -name '*.test.js' -o -name '*.test.jsx' \) -print
)
(( spec_found == 1 )) || fail \
  "no browser test suite found under frontend/; condition 6 requires browser tests"

printf 'frontend screens ok: %s section 8 screens declared with pages and a browser suite\n' \
  "${#required_screens[@]}"

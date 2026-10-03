#!/usr/bin/env bash
# Verify the cross-tenant security suite covers every layer SPEC.md section 13
# condition 3 names. Called by scripts/check_definition_of_done.sh [3/6].
#
# DoD condition 3 (SPEC.md section 13) requires "a security suite covers API,
# retrieval, background worker and artifact URL". The first cut of [3/6] passed
# on the suite directory merely existing, so an API-only suite could falsely turn
# `make done` green while three of the four named layers had no isolation test.
#
# The check is data-driven so a future cycle adds coverage without editing this
# script: `tests/security/covered-layers.txt` declares each covered layer as
# `<layer-id> <test-file>` per line, where the test file is relative to the
# security directory. Every canonical layer id must be declared, and each
# declared file must exist and contain at least one test. A missing layer, a
# missing or test-less file, an unknown or duplicate layer id is a named failure.
#
# Usage: check_security_coverage.sh <security-dir>
set -Eeuo pipefail

security_dir="${1:?security directory required}"

fail() { printf 'security coverage: %s\n' "$*" >&2; exit 1; }

[[ -d "$security_dir" ]] || fail \
  "tests/security/ is missing; the DoD requires the cross-tenant security suite"

# The four layers named by SPEC.md section 13 condition 3 and section 9.
required_layers=(api retrieval worker artifact-url)

manifest="$security_dir/covered-layers.txt"
[[ -f "$manifest" ]] || fail \
  "missing $manifest; declare each covered layer as '<layer-id> <test-file>'"

declare -A file_of
declare -A layer_seen
while read -r layer file _; do
  [[ -z "${layer:-}" || "$layer" == \#* ]] && continue
  [[ -n "${file:-}" ]] || fail \
    "manifest line for '$layer' needs a test file"
  case " ${required_layers[*]} " in
    *" $layer "*) ;;
    *) fail "unknown layer '$layer' in covered-layers.txt; expected one of: ${required_layers[*]}" ;;
  esac
  [[ -z "${layer_seen[$layer]:-}" ]] || fail "duplicate layer '$layer' in covered-layers.txt"
  layer_seen["$layer"]=1
  file_of["$layer"]="$file"
done < "$manifest"

# Canonical CSV of layers declared, so membership tests above cannot drift from
# the list this script prints and verifies.
missing=()
for layer in "${required_layers[@]}"; do
  [[ -n "${layer_seen[$layer]:-}" ]] || missing+=("$layer")
done
(( ${#missing[@]} == 0 )) || fail \
  "condition 3 layers not covered by the security suite: ${missing[*]}"

for layer in "${required_layers[@]}"; do
  file="$security_dir/${file_of[$layer]}"
  [[ -f "$file" ]] || fail \
    "declared $layer test file is missing: ${file_of[$layer]}"
  grep -q 'def test' "$file" || fail \
    "declared $layer test file has no test: ${file_of[$layer]}"
done

printf 'security coverage ok: %s condition 3 layers declared with tests\n' \
  "${#required_layers[@]}"

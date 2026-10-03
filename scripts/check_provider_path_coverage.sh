#!/usr/bin/env bash
# Verify the agent model provider path is proven the way SPEC.md section 13
# condition 5 requires. Called by scripts/check_definition_of_done.sh [2/6].
#
# DoD condition 5 (SPEC.md section 13) requires "Agent paths run deterministically
# in e2e, and the real provider path is proven: a deterministic fake model gateway
# drives the e2e; a separate live OpenRouter smoke passes and the LLM adapter logs
# model, prompt version, usage and trace id." The DoD gate never checked condition
# 5 at all, so once the other conditions turned green `make done` could pass with
# no deterministic agent path, no live provider proof and no attribution log --
# the same class of false stop condition the acceptance, security and screens
# checks closed for conditions 2, 3 and 6.
#
# The check is data-driven so a future cycle adds coverage without editing this
# script: `tests/unit/agents/covered-provider-paths.txt` declares each canonical
# part as `<part-id> <test-file>` (a path relative to the repository root) or
# `<part-id> uncovered <reason>`. Every canonical part id must be declared exactly
# once. A covered part's file must exist and contain at least one test. A part that
# is still `uncovered` keeps condition 5 unmet, so the gate fails and names the
# reason. An unknown or duplicate part id is refused.
#
# Usage: check_provider_path_coverage.sh <agents-dir> [repo-root]
set -Eeuo pipefail

agents_dir="${1:?agents test directory required}"
repo_root="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

fail() { printf 'provider path coverage: %s\n' "$*" >&2; exit 1; }

[[ -d "$agents_dir" ]] || fail \
  "tests/unit/agents/ is missing; the DoD requires the agent provider-path suite"

# The three parts named by SPEC.md section 13 condition 5.
required_parts=(
  deterministic-e2e
  live-openrouter-smoke
  attribution-log
)

manifest="$agents_dir/covered-provider-paths.txt"
[[ -f "$manifest" ]] || fail \
  "missing $manifest; declare each part as '<part-id> <test-file>' or '<part-id> uncovered <reason>'"

declare -A file_of
declare -A reason_of
declare -A part_seen
while read -r part second rest; do
  [[ -z "${part:-}" || "$part" == \#* ]] && continue
  case " ${required_parts[*]} " in
    *" $part "*) ;;
    *) fail "unknown part '$part' in covered-provider-paths.txt; expected one of: ${required_parts[*]}" ;;
  esac
  [[ -z "${part_seen[$part]:-}" ]] || fail "duplicate part '$part' in covered-provider-paths.txt"
  part_seen["$part"]=1
  if [[ "${second:-}" == "uncovered" ]]; then
    [[ -n "${rest:-}" ]] || fail "uncovered part '$part' needs a reason"
    reason_of["$part"]="$rest"
  elif [[ -n "${second:-}" ]]; then
    file_of["$part"]="$second"
  else
    fail "part '$part' needs a test file or 'uncovered <reason>'"
  fi
done < "$manifest"

missing=()
for part in "${required_parts[@]}"; do
  [[ -n "${part_seen[$part]:-}" ]] || missing+=("$part")
done
(( ${#missing[@]} == 0 )) || fail \
  "condition 5 provider-path parts not declared by the agents suite: ${missing[*]}"

uncovered_list=()
for part in "${required_parts[@]}"; do
  [[ -n "${reason_of[$part]:-}" ]] || continue
  uncovered_list+=("$part (${reason_of[$part]})")
done
(( ${#uncovered_list[@]} == 0 )) || fail \
  "condition 5 unmet; provider-path parts uncovered: ${uncovered_list[*]}"

for part in "${required_parts[@]}"; do
  file="$repo_root/${file_of[$part]}"
  [[ -f "$file" ]] || fail \
    "declared $part test file is missing: ${file_of[$part]}"
  grep -q 'def test' "$file" || fail \
    "declared $part test file has no test: ${file_of[$part]}"
done

printf 'provider path coverage ok: %s condition 5 parts declared with tests\n' \
  "${#required_parts[@]}"

#!/usr/bin/env bash
# Verify the section 11 acceptance scenarios have a green suite, the way SPEC.md
# section 13 condition 2 requires. Called by scripts/check_definition_of_done.sh
# [2/6].
#
# DoD condition 2 (SPEC.md section 13) requires "the section 11 acceptance
# scenarios pass; the acceptance suite is green". The first cut of [2/6] ran only
# the stage 0-10 e2e suite (condition 1), so `make done` could falsely turn green
# with no section 11 acceptance suite at all -- the same class of false stop
# condition the security and screens checks closed for conditions 3 and 6.
#
# The check is data-driven so a future cycle adds coverage without editing this
# script: `tests/acceptance/covered-scenarios.txt` declares each canonical
# scenario as `<scenario-id> <test-file>` (a path relative to the repository
# root) or `<scenario-id> uncovered <reason>`. Every canonical scenario id must be
# declared exactly once. A covered scenario's file must exist and contain at least
# one test. A scenario that is still `uncovered` keeps condition 2 unmet, so the
# gate fails and names the reason. An unknown or duplicate scenario id is refused.
#
# Usage: check_acceptance_coverage.sh <acceptance-dir> [repo-root]
set -Eeuo pipefail

acceptance_dir="${1:?acceptance directory required}"
repo_root="${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

fail() { printf 'acceptance coverage: %s\n' "$*" >&2; exit 1; }

[[ -d "$acceptance_dir" ]] || fail \
  "tests/acceptance/ is missing; the DoD requires the section 11 acceptance suite"

# The eight scenarios named by SPEC.md section 11 minimum acceptance scenarios.
# The database restore drill and the GitOps rollback drill are production-
# readiness gates, not prototype scenarios (ADR 0009, ADR 0010).
required_scenarios=(
  source-attribution
  known-requires-source
  unauthorized-approval-rejected
  method-change-identifies-dependents
  worker-restart-preserves-waiting
  duplicate-delivery-one-effect
  cross-client-retrieval-empty
  launch-blocked-on-failed-path
)

manifest="$acceptance_dir/covered-scenarios.txt"
[[ -f "$manifest" ]] || fail \
  "missing $manifest; declare each scenario as '<scenario-id> <test-file>' or '<scenario-id> uncovered <reason>'"

declare -A file_of
declare -A reason_of
declare -A scenario_seen
while read -r scenario second rest; do
  [[ -z "${scenario:-}" || "$scenario" == \#* ]] && continue
  case " ${required_scenarios[*]} " in
    *" $scenario "*) ;;
    *) fail "unknown scenario '$scenario' in covered-scenarios.txt; expected one of: ${required_scenarios[*]}" ;;
  esac
  [[ -z "${scenario_seen[$scenario]:-}" ]] || fail "duplicate scenario '$scenario' in covered-scenarios.txt"
  scenario_seen["$scenario"]=1
  if [[ "${second:-}" == "uncovered" ]]; then
    [[ -n "${rest:-}" ]] || fail "uncovered scenario '$scenario' needs a reason"
    reason_of["$scenario"]="$rest"
  elif [[ -n "${second:-}" ]]; then
    file_of["$scenario"]="$second"
  else
    fail "scenario '$scenario' needs a test file or 'uncovered <reason>'"
  fi
done < "$manifest"

# Canonical CSV of scenarios declared, so membership tests above cannot drift
# from the list this script prints and verifies.
missing=()
for scenario in "${required_scenarios[@]}"; do
  [[ -n "${scenario_seen[$scenario]:-}" ]] || missing+=("$scenario")
done
(( ${#missing[@]} == 0 )) || fail \
  "section 11 scenarios not declared by the acceptance suite: ${missing[*]}"

uncovered_list=()
for scenario in "${required_scenarios[@]}"; do
  [[ -n "${reason_of[$scenario]:-}" ]] || continue
  uncovered_list+=("$scenario (${reason_of[$scenario]})")
done
(( ${#uncovered_list[@]} == 0 )) || fail \
  "condition 2 unmet; section 11 scenarios uncovered: ${uncovered_list[*]}"

for scenario in "${required_scenarios[@]}"; do
  file="$repo_root/${file_of[$scenario]}"
  [[ -f "$file" ]] || fail \
    "declared $scenario test file is missing: ${file_of[$scenario]}"
  grep -q 'def test' "$file" || fail \
    "declared $scenario test file has no test: ${file_of[$scenario]}"
done

printf 'acceptance coverage ok: %s section 11 scenarios declared with tests\n' \
  "${#required_scenarios[@]}"

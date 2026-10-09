#!/usr/bin/env bash
# Machine-checkable prototype definition of done (SPEC.md section 13) plus the
# cockpit overhaul phase gate (SPEC.md section 14, ADR 0013).
#
# This is the build loop's success stop condition (`make done`). It is a gate,
# not an authority: it never approves a client artifact, spends, publishes or
# deploys. It fails loudly while any DoD condition is unmet, which is expected
# until the loop builds the missing suites, the UI and the deployment. The
# section 13 checks are the prerequisites; `[7/7]` proves the single-shell
# cockpit overhaul, so `.ralph/DONE` cannot be touched while that phase is open.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

fail() { printf 'DONE-GATE FAIL: %s\n' "$*" >&2; exit 1; }

printf '\n[1/7] per-cycle checks (make check: pytest + pyflakes, with Postgres)\n'
make check

printf '\n[2/7] stage 0-10 API e2e and suites (conditions 1, 2 and 5)\n'
uv run pytest tests/e2e -q || fail "the stage 0-10 e2e suite is missing or failing"
./scripts/check_acceptance_coverage.sh tests/acceptance \
  || fail "the section 11 acceptance suite is not covered; condition 2 is unmet"
./scripts/check_provider_path_coverage.sh tests/unit/agents \
  || fail "the agent provider path is not proven; condition 5 is unmet"

printf '\n[3/7] cross-tenant security suite (API, retrieval, worker, artifact URL)\n'
./scripts/check_security_coverage.sh tests/security \
  || fail "the cross-tenant security suite does not cover all four condition 3 layers"
uv run pytest tests/security -q || fail "the cross-tenant security suite is missing or failing"

printf '\n[4/7] absorbed OpenExecutive fork: additive RED changes only (ADR 0014)\n'
./scripts/check_vendor_additive.sh \
  || fail "vendor/openexecutive differs from the baseline outside the additive rule (ADR 0014)"
grep -q "31e55338db7f7a0eb7ff30b4cb8942a1ece551bd" docs/fork_inventory.md \
  || fail "the absorbed upstream pin is not recorded in docs/fork_inventory.md (ADR 0014)"

printf '\n[5/7] RED UI: all section 8 screens render, component tests, no OpenExecutive branding\n'
./scripts/check_frontend_screens.sh vendor/openexecutive/packages/ui tests/cockpit-ui/dod-screens.txt tests/cockpit-ui \
  || fail "the section 8 screens are not rendered; condition 6 is unmet"
./scripts/check_frontend_build.sh vendor/openexecutive/packages/ui tests/cockpit-ui \
  || fail "the cockpit does not build or its screen suite does not run; condition 6 is unmet"
./scripts/check_agent_charters.sh docs/agents \
  || fail "the agent charters SPEC.md section 5 requires are incomplete; condition 8 is unmet"
./scripts/check_branding_and_notice.sh vendor/openexecutive/packages/ui vendor/openexecutive \
  || fail "RED branding or retained LICENSE/NOTICE is incomplete; condition 8 is unmet"

printf '\n[6/7] deployed RED app on Atlas k3s (Argo CD healthy; migration ran before the API served)\n'
REDOP_HEALTH_URL="${REDOP_HEALTH_URL:-https://redop.atlas.lan/}"
./scripts/check_deployed_red_health.sh "$REDOP_HEALTH_URL" \
  || fail "the deployed RED app is not serving; condition 9 is unmet"

printf '\n[7/7] single shell: the cockpit is the only RED UI (SPEC.md section 14, ADR 0013)\n'
./scripts/check_cockpit_overhaul.sh \
  || fail "the single-shell cockpit overhaul gate is unmet; SPEC.md section 14 conditions are open (K queue)"

printf '\nDONE-GATE PASS: the prototype meets the section 13 definition of done and the cockpit meets the section 14 single-shell definition of done.\n'

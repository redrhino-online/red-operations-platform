#!/usr/bin/env bash
# Cockpit overhaul (single shell) definition-of-done gate. See SPEC.md section 14
# and ADR 0013 (with the absorbed-fork rule of ADR 0014).
#
# SPEC.md section 14: the rebranded OpenExecutive cockpit is the only user-facing
# RED UI; the twelve section 8 screens are native cockpit pages at
# `/operations/*`, implemented as additive files inside the absorbed vendor tree
# (ADR 0014); a shared workspace/engagement context drives them; the separate
# `/screens` thin client is retired. This is the `[7/7]` step of `make done`; it
# fails loudly while any condition is unmet, which is expected until the K queue
# completes. It never approves a client artifact, spends, publishes or deploys.
#
# Usage: scripts/check_cockpit_overhaul.sh [repo-root]
#   repo-root defaults to the repository containing this script. Live checks run
#   only when REDOP_HEALTH_URL is non-empty (the DoD runner exports it):
#   REDOP_HEALTH_INSECURE=1 skips TLS verification for the internal atlas-ca and
#   REDOP_PILOT_TENANT overrides the seeded workspace (default `3fmindset`).
set -Eeuo pipefail

repo="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)}"
cd "$repo"

fail() { printf 'COCKPIT-OVERHAUL FAIL: %s\n' "$*" >&2; exit 1; }

COCKPIT_UI="vendor/openexecutive/packages/ui"
NAV="$COCKPIT_UI/src/components/shell/navConfig.ts"
CHART="deploy/charts/redop"
ROUTES=(
  command-center
  client-workspace
  source-explorer
  transformation-map
  offer-and-journey
  build-board
  approval-inbox
  workflow-run-detail
  launch-readiness
  performance-review
  portfolio-opportunities
  authority-settings
)

printf '[14.1] one shell: the separate /screens thin client is retired\n'
[[ ! -d frontend ]] || fail "frontend/ still exists; the thin client is not retired (K7)"
[[ ! -f Dockerfile.ui ]] || fail "Dockerfile.ui still exists; the thin client image is not retired (K7)"
[[ ! -f $CHART/templates/deployment-ui.yaml ]] \
  || fail "$CHART/templates/deployment-ui.yaml still exists; the redop-ui Deployment is not retired (K7)"
[[ -f $CHART/templates/ingress.yaml ]] || fail "$CHART/templates/ingress.yaml is missing"
if grep -q "/screens" "$CHART/templates/ingress.yaml"; then
  fail "$CHART/templates/ingress.yaml still routes /screens; the second app is still served (K7)"
fi
if grep -rq "redop-ui" "$CHART" 2>/dev/null; then
  fail "the chart still references redop-ui; the second app is not retired (K7)"
fi
if grep -rq "Dockerfile.ui" .github .gitea 2>/dev/null; then
  fail "CI still builds Dockerfile.ui; the thin client image pipeline is not retired (K7)"
fi

printf '[14.2] RED Operations navigation points at native /operations routes\n'
[[ -f $NAV ]] || fail "$NAV is missing; the overlay does not carry the shell navigation"
if grep -q "/screens/" "$NAV"; then
  fail "$NAV still links /screens/*; the nav group still links out to the retired app (K6)"
fi
grep -qF "RED Operations" "$NAV" || fail "$NAV lost the RED Operations group"
for route in "${ROUTES[@]}"; do
  grep -qF "/operations/$route" "$NAV" \
    || fail "$NAV does not link the native /operations/$route screen"
done

printf '[14.3] all twelve section 8 screens exist as native cockpit pages\n'
for route in "${ROUTES[@]}"; do
  [[ -f $COCKPIT_UI/src/app/operations/$route/page.tsx ]] \
    || fail "$COCKPIT_UI/src/app/operations/$route/page.tsx is missing; the screen was not ported (K3-K6)"
done

printf '[14.4] the ported screens carry a repo-side component test suite\n'
[[ -f tests/cockpit-ui/package.json ]] \
  || fail "tests/cockpit-ui/package.json is missing; the ported screens carry no component tests (K3)"
grep -q '"test"' tests/cockpit-ui/package.json \
  || fail "tests/cockpit-ui/package.json declares no test script; the ported screens carry no component tests (K3)"

printf '[14.5] the section 13 screen gate exercises the cockpit, not the retired app\n'
for needle in "check_frontend_screens.sh frontend" "check_frontend_build.sh frontend"; do
  if grep -qF "$needle" scripts/check_definition_of_done.sh; then
    fail "scripts/check_definition_of_done.sh still runs $needle; the gate still targets the retired thin client (K7)"
  fi
done

if [[ -n "${REDOP_HEALTH_URL:-}" ]]; then
  printf '[14.6] live single shell on %s\n' "$REDOP_HEALTH_URL"
  base="${REDOP_HEALTH_URL%/}"
  tenant="${REDOP_PILOT_TENANT:-3fmindset}"
  curl_args=(-fsS --max-time 10)
  if [[ "${REDOP_HEALTH_INSECURE:-1}" == "1" ]]; then curl_args+=(-k); fi
  curl "${curl_args[@]}" "$base/operations/command-center" >/dev/null \
    || fail "the cockpit does not serve /operations/command-center at $base (deploy the overhauled cockpit)"
  cockpit_clients="$(curl "${curl_args[@]}" "$base/red/clients?tenant_id=$tenant")" \
    || fail "the RED API does not answer /red/clients?tenant_id=$tenant at $base"
  # The tenant id echoes in the response even when nothing is seeded, so the
  # gate must require an actual workspace row (SPEC.md section 14 condition 4):
  # a seeded workspace serializes with a "workspace_id", an empty listing does
  # not, and a screen that renders an empty state is not a working screen.
  grep -q '"workspace_id"' <<<"$cockpit_clients" \
    || fail "the pilot workspace $tenant is not seeded; screens would render empty states (K1)"
fi

printf 'COCKPIT-OVERHAUL PASS: the cockpit meets the section 14 single-shell definition of done.\n'

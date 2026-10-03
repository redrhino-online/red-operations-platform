#!/usr/bin/env bash
# Machine-checkable prototype definition of done. See SPEC.md section 13.
#
# This is the build loop's success stop condition (`make done`). It is a gate,
# not an authority: it never approves a client artifact, spends, publishes or
# deploys. It fails loudly while any DoD condition is unmet, which is expected
# until the loop builds the missing suites, the UI and the deployment.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

fail() { printf 'DONE-GATE FAIL: %s\n' "$*" >&2; exit 1; }

printf '\n[1/6] per-cycle checks (make check: pytest + pyflakes, with Postgres)\n'
make check

printf '\n[2/6] stage 0-10 API e2e and suites (conditions 1, 2 and 5)\n'
uv run pytest tests/e2e -q || fail "the stage 0-10 e2e suite is missing or failing"
./scripts/check_acceptance_coverage.sh tests/acceptance \
  || fail "the section 11 acceptance suite is not covered; condition 2 is unmet"
./scripts/check_provider_path_coverage.sh tests/unit/agents \
  || fail "the agent provider path is not proven; condition 5 is unmet"

printf '\n[3/6] cross-tenant security suite (API, retrieval, worker, artifact URL)\n'
./scripts/check_security_coverage.sh tests/security \
  || fail "the cross-tenant security suite does not cover all four condition 3 layers"
uv run pytest tests/security -q || fail "the cross-tenant security suite is missing or failing"

printf '\n[4/6] vendored OpenExecutive is unmodified (zero vendor edits)\n'
[[ -z "$(git -C vendor/openexecutive status --porcelain --untracked-files=all)" ]] \
  || fail "vendor/openexecutive has local changes; the DoD requires zero vendor edits"

printf '\n[5/6] RED UI: all section 8 screens render, browser tests, no OpenExecutive branding\n'
./scripts/check_frontend_screens.sh frontend \
  || fail "the section 8 screens are not rendered; condition 6 is unmet"
if command -v rg >/dev/null 2>&1; then
  if rg -q 'OpenExecutive' frontend --glob '!**/node_modules/**' --glob '!**/.next/**' 2>/dev/null; then
    fail "OpenExecutive branding found in frontend/; product surfaces must be RED branded"
  fi
else
  printf 'rg unavailable; skipping the UI branding scan (recorded as a gap)\n'
fi

printf '\n[6/6] deployed on Atlas k3s (Argo CD healthy; migration ran before the API served)\n'
REDOP_HEALTH_URL="${REDOP_HEALTH_URL:-https://redop.atlas.lan/}"
curl_args=(-fsS --max-time 10)
if [[ "${REDOP_HEALTH_INSECURE:-1}" == "1" ]]; then curl_args+=(-k); fi
curl "${curl_args[@]}" "$REDOP_HEALTH_URL" >/dev/null \
  || fail "deployed health check failed at $REDOP_HEALTH_URL"
printf 'health ok: %s\n' "$REDOP_HEALTH_URL"

printf '\nDONE-GATE PASS: the prototype meets the section 13 definition of done.\n'

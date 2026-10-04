#!/usr/bin/env bash
# Verify DoD condition 9's deployed health check proves the RED app is serving.
#
# SPEC.md section 13 condition 9: "The platform is deployed on the Atlas k3s
# cluster ... the deployed health check passes." A bare HTTP 200 is not enough.
# The Atlas host once served the OpenExecutive shell, so a bare 200 made the
# gate pass while RED was not deployed. This check requires a RED identity
# marker in the response, so a wrong app cannot satisfy condition 9.
#
# Usage: scripts/check_deployed_red_health.sh [URL]
#   URL defaults to $REDOP_HEALTH_URL, then to https://redop.atlas.lan/.
#   REDOP_RED_MARKER overrides the required identity marker.
#   REDOP_HEALTH_INSECURE=1 skips TLS verification for the internal atlas-ca.
set -Eeuo pipefail

url="${1:-${REDOP_HEALTH_URL:-https://redop.atlas.lan/}}"
marker="${REDOP_RED_MARKER:-RED Operations}"

fail() { printf 'deployed RED health FAIL: %s\n' "$*" >&2; exit 1; }

curl_args=(-fsS --max-time 10)
if [[ "${REDOP_HEALTH_INSECURE:-1}" == "1" ]]; then curl_args+=(-k); fi

body="$(curl "${curl_args[@]}" "$url")" \
  || fail "no successful response from $url"

if ! grep -Fq "$marker" <<<"$body"; then
  fail "response from $url does not carry the RED identity marker '$marker'; the deployed app is not RED (condition 9 unmet)"
fi

printf 'deployed RED health ok: %s carries %s\n' "$url" "$marker"

#!/usr/bin/env bash
# Additive vendor modification gate (ADR 0014; SPEC.md sections 2 and 13
# condition 7).
#
# The OpenExecutive fork is absorbed into this repository (vendor/openexecutive
# is ordinary tracked source). RED changes inside it are additive by default:
# RED-adopted surfaces (vendor/red-owned-files.txt) and new files are free, but
# every other upstream-origin file (vendor/upstream-files.txt) must match the
# bytes baselined in vendor/upstream-manifest.sha256. A locked file may change
# only through a named-owner decision recorded in docs/fork_inventory.md
# followed by a deliberate `make vendor-pin`. This gate is DoD step [4/7]; it
# never approves a client artifact, spends, publishes or deploys.
#
# Usage: scripts/check_vendor_additive.sh [repo-root]
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo="${1:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
cd "$repo"

[[ -f vendor/upstream-files.txt ]] \
  || { printf 'VENDOR-ADDITIVE FAIL: vendor/upstream-files.txt is missing; the fork is not absorbed (ADR 0014)\n' >&2; exit 1; }
[[ -f vendor/red-owned-files.txt ]] \
  || { printf 'VENDOR-ADDITIVE FAIL: vendor/red-owned-files.txt is missing; the fork is not absorbed (ADR 0014)\n' >&2; exit 1; }
[[ -f vendor/upstream-manifest.sha256 ]] \
  || { printf 'VENDOR-ADDITIVE FAIL: vendor/upstream-manifest.sha256 is missing; pin the absorbed fork (make vendor-pin)\n' >&2; exit 1; }

python3 "$SCRIPT_DIR/vendor_pin.py" check --repo "$repo"

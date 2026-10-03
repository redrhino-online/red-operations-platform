#!/usr/bin/env bash
# Verify the RED frontend compiles and runs its browser test suite. Called by
# scripts/check_definition_of_done.sh [5/6] after check_frontend_screens.sh.
#
# DoD condition 6 (SPEC.md section 13) requires the frontend to "build" and
# browser tests to "cover" the section 8 screens. The structural screens check
# only proves the screens, routes and a browser test file exist; it never
# compiles the UI nor runs its suite, so once the screens landed `make done`
# could stop on placeholder pages and a no-op test. This check closes that
# false-green: it requires a `build` and a `test` script in
# frontend/package.json and runs both, failing if either is missing or fails.
# It is a gate, not an authority: it approves nothing, spends nothing and
# deploys nothing.
#
# Usage: check_frontend_build.sh <frontend-dir>
set -Eeuo pipefail

frontend="${1:?frontend directory required}"

fail() { printf 'frontend build: %s\n' "$*" >&2; exit 1; }

[[ -d "$frontend" ]] || fail "frontend/ is missing"
[[ -f "$frontend/package.json" ]] || fail "missing $frontend/package.json"
package="$(realpath "$frontend/package.json")"

has_script() {
  node -e '
    const pkg = require(process.argv[1]);
    const name = process.argv[2];
    process.exit(pkg.scripts && pkg.scripts[name] ? 0 : 1);
  ' "$package" "$1" 2>/dev/null
}

has_script build || fail "frontend/package.json declares no 'build' script"
has_script test || fail \
  "frontend/package.json declares no 'test' script; the browser suite is not runnable"

( cd "$frontend" && npm run build ) \
  || fail "frontend does not build (npm run build failed)"
( cd "$frontend" && npm test ) \
  || fail "frontend browser suite failed (npm test)"

printf 'frontend build ok: build compiled and the browser suite ran\n'

#!/usr/bin/env bash
# Verify the RED cockpit compiles and its screen component suite runs. Called by
# scripts/check_definition_of_done.sh [5/7] after check_frontend_screens.sh.
#
# DoD condition 6 (SPEC.md section 13) requires the UI to "build" and tests to
# "cover" the section 8 screens. The structural screens check only proves the
# screens, routes and a test file exist; it never compiles the cockpit nor runs
# its suite, so once the screens landed `make done` could stop on placeholder
# pages and a no-op test. This check closes that false-green: it requires the
# cockpit package to declare a `build` script and the repo-side component suite
# to declare a `test` script, then runs both, failing if either is missing or
# fails. Since the single-shell overhaul (SPEC.md section 14, ADR 0013) the
# cockpit is the only UI, so this exercises the cockpit pages, not the retired
# `/screens` thin client. It is a gate, not an authority: it approves nothing,
# spends nothing and deploys nothing.
#
# Usage: check_frontend_build.sh <cockpit-ui-dir> <test-dir>
set -Eeuo pipefail

cockpit="${1:?cockpit UI directory required}"
test_dir="${2:?component test directory required}"

fail() { printf 'cockpit build: %s\n' "$*" >&2; exit 1; }

[[ -d "$cockpit" ]] || fail "cockpit UI directory '$cockpit' is missing"
[[ -f "$cockpit/package.json" ]] || fail "missing $cockpit/package.json"
[[ -d "$test_dir" ]] || fail "component test directory '$test_dir' is missing"
[[ -f "$test_dir/package.json" ]] || fail "missing $test_dir/package.json"

has_script() { # $1=package.json $2=script name
  node -e '
    const pkg = require(process.argv[1]);
    const name = process.argv[2];
    process.exit(pkg.scripts && pkg.scripts[name] ? 0 : 1);
  ' "$(realpath "$1")" "$2" 2>/dev/null
}

has_script "$cockpit/package.json" build || fail \
  "$cockpit/package.json declares no 'build' script"
has_script "$test_dir/package.json" test || fail \
  "$test_dir/package.json declares no 'test' script; the screen suite is not runnable"

( cd "$cockpit" && npm run build ) \
  || fail "the cockpit does not build (npm run build failed)"
( cd "$test_dir" && npm test ) \
  || fail "the cockpit screen suite failed (npm test)"

printf 'cockpit build ok: the cockpit compiled and the screen suite ran\n'

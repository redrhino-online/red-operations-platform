"""Behavioral tests for the cockpit build and screen-suite gate.

SPEC.md section 13 condition 6 requires the UI to build and tests to cover the
section 8 screens. Since the single-shell overhaul (SPEC.md section 14, ADR 0013)
the cockpit is the only UI, so ``scripts/check_frontend_build.sh`` requires the
cockpit package to declare a ``build`` script and the repo-side component suite
to declare a ``test`` script, then runs both. These tests pin that contract.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK = REPO_ROOT / "scripts" / "check_frontend_build.sh"

FAKE_NPM = """#!/usr/bin/env bash
set -Eeuo pipefail
printf 'npm %s\\n' "$*" >> "$FAKE_NPM_LOG"
case "${1:-}" in
  test) exit "${FAKE_NPM_TEST_RC:-0}" ;;
  run)  exit "${FAKE_NPM_BUILD_RC:-0}" ;;
  *)    exit 0 ;;
esac
"""


def write_package(directory: Path, scripts: dict[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "package.json").write_text(
        json.dumps({"name": "test-ui", "scripts": scripts}), encoding="utf-8"
    )


def run_check(
    cockpit: Path, test_dir: Path, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CHECK), str(cockpit), str(test_dir)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(env or {})},
    )


class CockpitBuildCheckTests(unittest.TestCase):
    def _fake_npm(self, root: Path) -> tuple[Path, Path]:
        bindir = root / "bin"
        bindir.mkdir(parents=True, exist_ok=True)
        npm = bindir / "npm"
        npm.write_text(FAKE_NPM, encoding="utf-8")
        npm.chmod(0o755)
        log = root / "npm.log"
        return bindir, log

    def _run_with_fake_npm(
        self,
        root: Path,
        cockpit: Path,
        test_dir: Path,
        *,
        build_rc: str = "0",
        test_rc: str = "0",
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        bindir, log = self._fake_npm(root)
        result = run_check(
            cockpit,
            test_dir,
            env={
                "PATH": f"{bindir}:{os.environ['PATH']}",
                "FAKE_NPM_LOG": str(log),
                "FAKE_NPM_BUILD_RC": build_rc,
                "FAKE_NPM_TEST_RC": test_rc,
            },
        )
        return result, log

    def test_complete_cockpit_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cockpit = root / "cockpit"
            test_dir = root / "tests" / "cockpit-ui"
            write_package(cockpit, {"build": "next build"})
            write_package(test_dir, {"test": "vitest run"})
            result, log = self._run_with_fake_npm(root, cockpit, test_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("cockpit build ok", result.stdout)
            self.assertIn("npm run build", log.read_text(encoding="utf-8"))
            self.assertIn("npm test", log.read_text(encoding="utf-8"))

    def test_missing_cockpit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            test_dir = root / "tests" / "cockpit-ui"
            write_package(test_dir, {"test": "vitest run"})
            result = run_check(root / "missing", test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("is missing", result.stderr)

    def test_missing_cockpit_package_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cockpit = root / "cockpit"
            cockpit.mkdir()
            test_dir = root / "tests" / "cockpit-ui"
            write_package(test_dir, {"test": "vitest run"})
            result = run_check(cockpit, test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("package.json", result.stderr)

    def test_missing_build_script_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cockpit = root / "cockpit"
            test_dir = root / "tests" / "cockpit-ui"
            write_package(cockpit, {"dev": "next dev"})
            write_package(test_dir, {"test": "vitest run"})
            result, log = self._run_with_fake_npm(root, cockpit, test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("no 'build' script", result.stderr)
            self.assertFalse(log.exists())

    def test_missing_test_script_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cockpit = root / "cockpit"
            test_dir = root / "tests" / "cockpit-ui"
            write_package(cockpit, {"build": "next build"})
            write_package(test_dir, {"dev": "vitest"})
            result, log = self._run_with_fake_npm(root, cockpit, test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("no 'test' script", result.stderr)
            self.assertFalse(log.exists())

    def test_failing_build_fails_and_skips_suite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cockpit = root / "cockpit"
            test_dir = root / "tests" / "cockpit-ui"
            write_package(cockpit, {"build": "next build"})
            write_package(test_dir, {"test": "vitest run"})
            result, log = self._run_with_fake_npm(
                root, cockpit, test_dir, build_rc="1"
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("does not build", result.stderr)
            self.assertNotIn("npm test", log.read_text(encoding="utf-8"))

    def test_failing_suite_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cockpit = root / "cockpit"
            test_dir = root / "tests" / "cockpit-ui"
            write_package(cockpit, {"build": "next build"})
            write_package(test_dir, {"test": "vitest run"})
            result, _ = self._run_with_fake_npm(
                root, cockpit, test_dir, test_rc="1"
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("screen suite failed", result.stderr)


if __name__ == "__main__":
    unittest.main()

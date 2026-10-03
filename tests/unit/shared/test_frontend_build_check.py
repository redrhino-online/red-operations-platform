"""Behavioral tests for the frontend build and suite gate.

SPEC.md section 13 condition 6 requires the frontend to build and browser tests
to cover the section 8 screens. ``scripts/check_frontend_screens.sh`` only
proves the screens, routes and a test file exist, so it could pass on
placeholder pages and a no-op test and let ``make done`` stop without the UI
ever compiling. These tests pin the stricter contract in
``scripts/check_frontend_build.sh``: ``frontend/package.json`` must declare a
``build`` and a ``test`` script, and both must run and succeed.
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


def write_package(frontend: Path, scripts: dict[str, str]) -> None:
    frontend.mkdir(parents=True, exist_ok=True)
    (frontend / "package.json").write_text(
        json.dumps({"name": "test-ui", "scripts": scripts}), encoding="utf-8"
    )


def run_check(
    frontend: Path, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CHECK), str(frontend)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(env or {})},
    )


class FrontendBuildCheckTests(unittest.TestCase):
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
        frontend: Path,
        *,
        build_rc: str = "0",
        test_rc: str = "0",
    ) -> tuple[subprocess.CompletedProcess[str], Path]:
        bindir, log = self._fake_npm(root)
        result = run_check(
            frontend,
            env={
                "PATH": f"{bindir}:{os.environ['PATH']}",
                "FAKE_NPM_LOG": str(log),
                "FAKE_NPM_BUILD_RC": build_rc,
                "FAKE_NPM_TEST_RC": test_rc,
            },
        )
        return result, log

    def test_complete_frontend_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frontend = root / "frontend"
            write_package(frontend, {"build": "next build", "test": "playwright test"})
            result, log = self._run_with_fake_npm(root, frontend)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("frontend build ok", result.stdout)
            self.assertIn("npm run build", log.read_text(encoding="utf-8"))
            self.assertIn("npm test", log.read_text(encoding="utf-8"))

    def test_missing_frontend_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check(Path(tmp) / "frontend")
            self.assertEqual(result.returncode, 1)
            self.assertIn("frontend/ is missing", result.stderr)

    def test_missing_package_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frontend = Path(tmp) / "frontend"
            frontend.mkdir()
            result = run_check(frontend)
            self.assertEqual(result.returncode, 1)
            self.assertIn("package.json", result.stderr)

    def test_missing_build_script_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frontend = root / "frontend"
            write_package(frontend, {"test": "playwright test"})
            result, log = self._run_with_fake_npm(root, frontend)
            self.assertEqual(result.returncode, 1)
            self.assertIn("no 'build' script", result.stderr)
            self.assertFalse(log.exists())

    def test_missing_test_script_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frontend = root / "frontend"
            write_package(frontend, {"build": "next build"})
            result, log = self._run_with_fake_npm(root, frontend)
            self.assertEqual(result.returncode, 1)
            self.assertIn("no 'test' script", result.stderr)
            self.assertFalse(log.exists())

    def test_failing_build_fails_and_skips_suite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frontend = root / "frontend"
            write_package(frontend, {"build": "next build", "test": "playwright test"})
            result, log = self._run_with_fake_npm(root, frontend, build_rc="1")
            self.assertEqual(result.returncode, 1)
            self.assertIn("does not build", result.stderr)
            self.assertNotIn("npm test", log.read_text(encoding="utf-8"))

    def test_failing_suite_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frontend = root / "frontend"
            write_package(frontend, {"build": "next build", "test": "playwright test"})
            result, _ = self._run_with_fake_npm(root, frontend, test_rc="1")
            self.assertEqual(result.returncode, 1)
            self.assertIn("browser suite failed", result.stderr)


if __name__ == "__main__":
    unittest.main()

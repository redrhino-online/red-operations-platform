"""Behavioral tests for the condition 3 security coverage gate.

SPEC.md section 13 condition 3 requires "a security suite covers API, retrieval,
background worker and artifact URL". The DoD script's first cut passed on
``tests/security`` merely existing, so an API-only suite could falsely turn
``make done`` green while three named layers had no isolation test. These tests
pin the stricter contract in ``scripts/check_security_coverage.sh``: the suite
declares each covered layer in ``tests/security/covered-layers.txt``, every
canonical layer is declared, and each declared file exists with at least one
test.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK = REPO_ROOT / "scripts" / "check_security_coverage.sh"

LAYERS = ("api", "retrieval", "worker", "artifact-url")
FILE = {layer: f"test_{layer.replace('-', '_')}.py" for layer in LAYERS}


def run_check(security: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CHECK), str(security)],
        capture_output=True,
        text=True,
        check=False,
    )


def build_security(
    root: Path,
    *,
    layers: tuple[str, ...] = LAYERS,
    file_for: tuple[str, ...] = LAYERS,
    tests_for: tuple[str, ...] = LAYERS,
) -> Path:
    security = root / "security"
    security.mkdir(parents=True, exist_ok=True)
    (security / "covered-layers.txt").write_text(
        "".join(f"{layer} {FILE[layer]}\n" for layer in layers),
        encoding="utf-8",
    )
    for layer in file_for:
        body = "def test_ok():\n    assert True\n" if layer in tests_for else "# no tests\n"
        (security / FILE[layer]).write_text(body, encoding="utf-8")
    return security


class SecurityCoverageCheckTests(unittest.TestCase):
    def test_a_complete_suite_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check(build_security(Path(tmp)))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("4 condition 3 layers", result.stdout)

    def test_missing_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check(Path(tmp) / "security")
            self.assertEqual(result.returncode, 1)
            self.assertIn("tests/security/ is missing", result.stderr)

    def test_missing_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            security = Path(tmp) / "security"
            security.mkdir()
            result = run_check(security)
            self.assertEqual(result.returncode, 1)
            self.assertIn("covered-layers.txt", result.stderr)

    def test_uncovered_layer_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            security = build_security(Path(tmp), layers=LAYERS[:-1])
            result = run_check(security)
            self.assertEqual(result.returncode, 1)
            self.assertIn("artifact-url", result.stderr)

    def test_unknown_layer_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            security = build_security(Path(tmp))
            manifest = security / "covered-layers.txt"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "queue test_queue.py\n",
                encoding="utf-8",
            )
            result = run_check(security)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown layer 'queue'", result.stderr)

    def test_declared_file_missing_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            security = build_security(Path(tmp), file_for=LAYERS[:-1])
            result = run_check(security)
            self.assertEqual(result.returncode, 1)
            self.assertIn("declared artifact-url test file is missing", result.stderr)

    def test_declared_file_without_tests_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            security = build_security(Path(tmp), tests_for=LAYERS[:-1])
            result = run_check(security)
            self.assertEqual(result.returncode, 1)
            self.assertIn("declared artifact-url test file has no test", result.stderr)

    def test_repository_suite_is_honest(self) -> None:
        # The real suite covers all four condition 3 layers today (API,
        # retrieval, worker and artifact-url), so the gate must pass and must
        # not name any layer as missing.
        result = run_check(REPO_ROOT / "tests" / "security")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("security coverage ok", result.stdout)
        self.assertNotIn("not covered", result.stderr)
        for layer in LAYERS:
            self.assertNotIn(layer, result.stderr)


if __name__ == "__main__":
    unittest.main()

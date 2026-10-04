"""Behavioral tests for the condition 2 acceptance coverage gate.

SPEC.md section 13 condition 2 requires "the section 11 acceptance scenarios
pass; the acceptance suite is green". The DoD script's first cut ran only the
stage 0-10 e2e suite (condition 1), so ``make done`` could falsely turn green
with no section 11 acceptance suite at all. These tests pin the stricter contract
in ``scripts/check_acceptance_coverage.sh``: the suite declares each canonical
scenario in ``tests/acceptance/covered-scenarios.txt`` as either a test file or an
explicit ``uncovered`` reason, every canonical scenario is declared, and a covered
file exists with at least one test. An ``uncovered`` scenario keeps condition 2
unmet.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK = REPO_ROOT / "scripts" / "check_acceptance_coverage.sh"

SCENARIOS = (
    "source-attribution",
    "known-requires-source",
    "unauthorized-approval-rejected",
    "method-change-identifies-dependents",
    "worker-restart-preserves-waiting",
    "duplicate-delivery-one-effect",
    "cross-client-retrieval-empty",
    "launch-blocked-on-failed-path",
    "gitops-revert-restores",
)
FILE = {
    scenario: f"tests/unit/acceptance/test_{scenario.replace('-', '_')}.py"
    for scenario in SCENARIOS
}


def run_check(
    acceptance: Path, repo_root: Path | None = None
) -> subprocess.CompletedProcess[str]:
    args = ["bash", str(CHECK), str(acceptance)]
    if repo_root is not None:
        args.append(str(repo_root))
    return subprocess.run(args, capture_output=True, text=True, check=False)


def build_acceptance(
    root: Path,
    *,
    scenarios: tuple[str, ...] = SCENARIOS,
    file_for: tuple[str, ...] = SCENARIOS,
    tests_for: tuple[str, ...] = SCENARIOS,
    uncovered: tuple[str, ...] = (),
) -> Path:
    acceptance = root / "acceptance"
    acceptance.mkdir(parents=True, exist_ok=True)
    lines = []
    for scenario in scenarios:
        if scenario in uncovered:
            lines.append(f"{scenario} uncovered pending\n")
        else:
            lines.append(f"{scenario} {FILE[scenario]}\n")
    (acceptance / "covered-scenarios.txt").write_text(
        "".join(lines), encoding="utf-8"
    )
    for scenario in file_for:
        if scenario in uncovered:
            continue
        path = root / FILE[scenario]
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "def test_ok():\n    assert True\n" if scenario in tests_for else "# none\n"
        path.write_text(body, encoding="utf-8")
    return acceptance


class AcceptanceCoverageCheckTests(unittest.TestCase):
    def test_a_complete_suite_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_check(build_acceptance(root), root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("9 section 11 scenarios", result.stdout)

    def test_missing_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check(Path(tmp) / "acceptance")
            self.assertEqual(result.returncode, 1)
            self.assertIn("tests/acceptance/ is missing", result.stderr)

    def test_missing_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            acceptance = Path(tmp) / "acceptance"
            acceptance.mkdir()
            result = run_check(acceptance)
            self.assertEqual(result.returncode, 1)
            self.assertIn("covered-scenarios.txt", result.stderr)

    def test_uncovered_scenario_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acceptance = build_acceptance(root, uncovered=("gitops-revert-restores",))
            result = run_check(acceptance, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("condition 2 unmet", result.stderr)
            self.assertIn("gitops-revert-restores", result.stderr)

    def test_undeclared_scenario_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acceptance = build_acceptance(root, scenarios=SCENARIOS[:-1])
            result = run_check(acceptance, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("gitops-revert-restores", result.stderr)

    def test_unknown_scenario_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acceptance = build_acceptance(root)
            manifest = acceptance / "covered-scenarios.txt"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "teapot tests/unit/x.py\n",
                encoding="utf-8",
            )
            result = run_check(acceptance, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown scenario 'teapot'", result.stderr)

    def test_duplicate_scenario_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acceptance = build_acceptance(root)
            manifest = acceptance / "covered-scenarios.txt"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + f"source-attribution {FILE['source-attribution']}\n",
                encoding="utf-8",
            )
            result = run_check(acceptance, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate scenario 'source-attribution'", result.stderr)

    def test_declared_file_missing_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acceptance = build_acceptance(root, file_for=SCENARIOS[:-1])
            result = run_check(acceptance, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "declared gitops-revert-restores test file is missing",
                result.stderr,
            )

    def test_declared_file_without_tests_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            acceptance = build_acceptance(root, tests_for=SCENARIOS[:-1])
            result = run_check(acceptance, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "declared gitops-revert-restores test file has no test",
                result.stderr,
            )

    def test_repository_suite_is_honest(self) -> None:
        # One section 11 scenario has no test yet, so the gate must fail and name
        # it rather than passing condition 2. The retrieval and duplicate-delivery
        # scenarios are now covered, so neither may be listed as unmet. Database
        # backup restore is not a prototype scenario (ADR 0009).
        result = run_check(REPO_ROOT / "tests" / "acceptance")
        self.assertEqual(result.returncode, 1)
        self.assertIn("gitops-revert-restores", result.stderr)
        self.assertNotIn("backup-restores-approval-trail", result.stderr)
        self.assertNotIn("cross-client-retrieval-empty", result.stderr)
        self.assertNotIn("duplicate-delivery-one-effect", result.stderr)


if __name__ == "__main__":
    unittest.main()

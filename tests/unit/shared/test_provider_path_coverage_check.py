"""Behavioral tests for the condition 5 provider-path coverage gate.

SPEC.md section 13 condition 5 requires "Agent paths run deterministically in e2e,
and the real provider path is proven". The DoD script never checked condition 5,
so ``make done`` could falsely turn green with no deterministic agent path and no
live provider proof. These tests pin the stricter contract in
``scripts/check_provider_path_coverage.sh``: the agents suite declares each
canonical part in ``tests/unit/agents/covered-provider-paths.txt`` as either a test
file or an explicit ``uncovered`` reason, every canonical part is declared, and a
covered file exists with at least one test. An ``uncovered`` part keeps condition
5 unmet.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK = REPO_ROOT / "scripts" / "check_provider_path_coverage.sh"

PARTS = (
    "deterministic-e2e",
    "live-openrouter-smoke",
    "attribution-log",
)
FILE = {
    part: f"tests/unit/agents/test_{part.replace('-', '_')}.py" for part in PARTS
}


def run_check(agents: Path, repo_root: Path | None = None) -> subprocess.CompletedProcess[str]:
    args = ["bash", str(CHECK), str(agents)]
    if repo_root is not None:
        args.append(str(repo_root))
    return subprocess.run(args, capture_output=True, text=True, check=False)


def build_agents(
    root: Path,
    *,
    parts: tuple[str, ...] = PARTS,
    file_for: tuple[str, ...] = PARTS,
    tests_for: tuple[str, ...] = PARTS,
    uncovered: tuple[str, ...] = (),
) -> Path:
    agents = root / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    lines = []
    for part in parts:
        if part in uncovered:
            lines.append(f"{part} uncovered pending\n")
        else:
            lines.append(f"{part} {FILE[part]}\n")
    (agents / "covered-provider-paths.txt").write_text("".join(lines), encoding="utf-8")
    for part in file_for:
        if part in uncovered:
            continue
        path = root / FILE[part]
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "def test_ok():\n    assert True\n" if part in tests_for else "# none\n"
        path.write_text(body, encoding="utf-8")
    return agents


class ProviderPathCoverageCheckTests(unittest.TestCase):
    def test_a_complete_suite_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = run_check(build_agents(root), root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("3 condition 5 parts", result.stdout)

    def test_missing_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check(Path(tmp) / "agents")
            self.assertEqual(result.returncode, 1)
            self.assertIn("tests/unit/agents/ is missing", result.stderr)

    def test_missing_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agents = Path(tmp) / "agents"
            agents.mkdir()
            result = run_check(agents)
            self.assertEqual(result.returncode, 1)
            self.assertIn("covered-provider-paths.txt", result.stderr)

    def test_uncovered_part_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = build_agents(root, uncovered=("live-openrouter-smoke",))
            result = run_check(agents, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("condition 5 unmet", result.stderr)
            self.assertIn("live-openrouter-smoke", result.stderr)

    def test_undeclared_part_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = build_agents(root, parts=PARTS[:-1])
            result = run_check(agents, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("attribution-log", result.stderr)

    def test_unknown_part_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = build_agents(root)
            manifest = agents / "covered-provider-paths.txt"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "teapot tests/unit/x.py\n",
                encoding="utf-8",
            )
            result = run_check(agents, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown part 'teapot'", result.stderr)

    def test_duplicate_part_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = build_agents(root)
            manifest = agents / "covered-provider-paths.txt"
            manifest.write_text(
                manifest.read_text(encoding="utf-8")
                + f"attribution-log {FILE['attribution-log']}\n",
                encoding="utf-8",
            )
            result = run_check(agents, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate part 'attribution-log'", result.stderr)

    def test_declared_file_missing_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = build_agents(root, file_for=PARTS[:-1])
            result = run_check(agents, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("declared attribution-log test file is missing", result.stderr)

    def test_declared_file_without_tests_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = build_agents(root, tests_for=PARTS[:-1])
            result = run_check(agents, root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("declared attribution-log test file has no test", result.stderr)

    def test_repository_suite_is_honest(self) -> None:
        # The deterministic e2e agent path and the live smoke proof do not exist
        # yet, so the gate must fail and name them rather than passing condition 5.
        result = run_check(REPO_ROOT / "tests" / "unit" / "agents")
        self.assertEqual(result.returncode, 1)
        self.assertIn("deterministic-e2e", result.stderr)
        self.assertIn("live-openrouter-smoke", result.stderr)
        self.assertNotIn("attribution-log (", result.stderr)


if __name__ == "__main__":
    unittest.main()

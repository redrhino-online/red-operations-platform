from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_SCRIPT = REPO_ROOT / "scripts/ralph_state.py"


def seed_repo(root: Path) -> None:
    (root / "docs").mkdir()
    (root / ".ralph").mkdir()
    (root / "IMPLEMENTATION_PLAN.md").write_text(
        "# Plan\n\n"
        "## Current cycle status\n\n"
        "### Cycle current: G1 done\n"
        "- **Selected item:** G1 lead-magnet kit.\n"
        "- **Outcome:** Typed artifact implemented.\n"
        "- **Evidence:** 14 tests pass.\n"
        "- **Next ready item:** G2 authority-video kit, no unmet dependency.\n\n"
        "### Cycle previous: C4 done\n"
        "- Historical record.\n\n"
        "### Owner directive old\n"
        "- Must remain available in history.\n\n"
        "## Prototype definition of done\n"
        "- make done passes.\n\n"
        "| # | Item | Area | Depends | Evidence / gate |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| G1 | Lead magnet kit | commercial | — | **Done 2026-10-06** |\n"
        "| G2 | Authority video kit | production | — | typed artifact test |\n"
        "| G9 | Source acquisition | process | — | unresolved; license-owner request |\n"
        "| W1 | Worker | deploy | — | worker health |\n"
        "| Q16 | Stale mutation | api | Q15 | Remaining: stale second write returns 409 |\n",
        encoding="utf-8",
    )


class RalphStateTests(unittest.TestCase):
    def run_state(self, root: Path, mode: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(STATE_SCRIPT), mode, str(root)],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_initialize_archives_old_entries_and_generates_bounded_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_repo(root)

            result = self.run_state(root, "initialize")

            self.assertEqual(result.returncode, 0, result.stderr)
            plan = (root / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
            history = (root / "docs/plan-history.md").read_text(encoding="utf-8")
            state = (root / ".ralph/STATE.md").read_text(encoding="utf-8")
            self.assertIn("Cycle current: G1 done", plan)
            self.assertIn("Cycle previous: C4 done", plan)
            self.assertNotIn("Owner directive old", plan)
            self.assertIn("Owner directive old", history)
            self.assertIn("Next ready: G2 authority-video kit", state)
            self.assertIn("G1 [done; commercial; depends —]", state)
            self.assertIn("G2 [open; production; depends —]", state)
            self.assertIn("G9 [blocked on owner input; process; depends —]", state)
            self.assertIn("W1 [open; deploy; depends —]", state)
            self.assertIn("Q16 [partial; api; depends Q15]", state)
            self.assertLess(len(state.encode("utf-8")), 4096)

    def test_finish_archives_entries_older_than_two_and_refreshes_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed_repo(root)
            self.run_state(root, "initialize")
            plan_path = root / "IMPLEMENTATION_PLAN.md"
            plan = plan_path.read_text(encoding="utf-8")
            plan_path.write_text(
                plan.replace(
                    "## Current cycle status\n\n",
                    "## Current cycle status\n\n"
                    "### Cycle newest: G2 done\n"
                    "- **Selected item:** G2 authority-video kit.\n"
                    "- **Next ready item:** G4 strategy-session kit.\n\n",
                    1,
                ),
                encoding="utf-8",
            )

            result = self.run_state(root, "finish")

            self.assertEqual(result.returncode, 0, result.stderr)
            plan = plan_path.read_text(encoding="utf-8")
            history = (root / "docs/plan-history.md").read_text(encoding="utf-8")
            state = (root / ".ralph/STATE.md").read_text(encoding="utf-8")
            self.assertIn("Cycle newest: G2 done", plan)
            self.assertIn("Cycle current: G1 done", plan)
            self.assertNotIn("Cycle previous: C4 done", plan)
            self.assertIn("Cycle previous: C4 done", history)
            self.assertIn("Next ready: G4 strategy-session kit", state)


if __name__ == "__main__":
    unittest.main()

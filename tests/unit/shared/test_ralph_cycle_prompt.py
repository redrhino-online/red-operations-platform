from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RALPH_CYCLE = REPO_ROOT / "ralph_cycle.sh"


class RalphCyclePromptTests(unittest.TestCase):
    def test_prompt_preserves_inline_shell_syntax_and_expands_only_paths(self) -> None:
        env = os.environ.copy()
        env.update(
            {
                "RALPH_PROMPT_TEST": "1",
                "RALPH_DB_PREFLIGHT": "0",
                "RALPH_OPENCODE": "true",
            }
        )
        result = subprocess.run(
            [str(RALPH_CYCLE), str(REPO_ROOT)],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Work in the repository at {REPO_ROOT}.", result.stdout)
        self.assertIn(f"Spec (authoritative): {REPO_ROOT}/SPEC.md", result.stdout)
        self.assertIn("never push to `upstream`", result.stdout)
        self.assertNotRegex(result.stdout, r"@[A-Z_]+@")
        self.assertNotIn("command not found", result.stderr)


if __name__ == "__main__":
    unittest.main()

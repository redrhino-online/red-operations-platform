from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RALPH_CYCLE = REPO_ROOT / "ralph_cycle.sh"


class RalphCyclePromptTests(unittest.TestCase):
    def test_prompt_uses_stable_first_order_and_harness_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "IMPLEMENTATION_PLAN.md").write_text(
                "# Plan\n\n"
                "## Current cycle status\n\n"
                "### Cycle fixture\n"
                "- **Selected item:** fixture.\n"
                "- **Outcome:** fixture handoff.\n"
                "- **Evidence:** fixture tests pass.\n"
                "- **Next ready item:** fixture next, no dependency.\n\n"
                "## Prototype definition of done\n\n"
                "## Canon gap backlog\n\n"
                "| # | Item | Area | Depends | Evidence / gate |\n"
                "| --- | --- | --- | --- | --- |\n"
                "| G2 | Fixture next | production | — | test |\n",
                encoding="utf-8",
            )
            lock = repo / ".ralph/cycle.lock"
            lock.mkdir(parents=True)
            (lock / "pid").write_text(f"{os.getpid()}\n", encoding="utf-8")
            (lock / "started").write_text("test\n", encoding="utf-8")
            config_path = repo / ".ralph/opencode.json"
            env = os.environ.copy()
            env.update(
                {
                    "RALPH_PROMPT_TEST": "1",
                    "RALPH_DB_PREFLIGHT": "0",
                    "RALPH_OPENCODE": "true",
                    "RALPH_OPENCODE_CONFIG": str(config_path),
                }
            )
            result = subprocess.run(
                [str(RALPH_CYCLE), str(repo)],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=15,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f"Repo: {repo}.", result.stdout)
            self.assertIn(f"Read {REPO_ROOT}/SPEC.md once, fully.", result.stdout)
            self.assertIn(f"{repo}/.ralph/STATE.md", result.stdout)
            self.assertIn("`git status`, `git log -5`", result.stdout)
            self.assertNotRegex(result.stdout, r"@[A-Z_]+@")
            self.assertNotIn("command not found", result.stderr)
            stable_spec = result.stdout.index("Read ")
            memories = result.stdout.index("Read Serena memories")
            state = result.stdout.index("Read generated")
            plan = result.stdout.index("Read only selected plan rows")
            volatile = result.stdout.index("Last, inspect")
            self.assertLess(stable_spec, memories)
            self.assertLess(memories, state)
            self.assertLess(state, plan)
            self.assertLess(plan, volatile)

            config = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertFalse(config["snapshot"])
            self.assertEqual(
                config["instructions"],
                [str(REPO_ROOT / ".opencode/instructions/ralph.md")],
            )
            self.assertEqual(config["compaction"]["preserve_recent_tokens"], 80000)
            instructions = Path(config["instructions"][0]).read_text(encoding="utf-8")
            self.assertIn("Never push to `upstream`.", instructions)


if __name__ == "__main__":
    unittest.main()

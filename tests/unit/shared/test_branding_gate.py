"""Behavioral tests for the condition 8 branding and charter gates.

SPEC.md section 13 condition 8 requires "the Director name, agent charters and
UI copy are RED with no OpenExecutive branding in user facing surfaces, and
LICENSE and NOTICE are retained". These tests pin the stricter contract added in
``scripts/check_agent_charters.sh`` (every section 5 agent has a charter carrying
the required operating-contract sections, declared in
``docs/agents/agent-charters.txt``) and ``scripts/check_branding_and_notice.sh``
(RED Director name, no OpenExecutive branding, vendored LICENSE/NOTICE retained).
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHARTERS = REPO_ROOT / "scripts" / "check_agent_charters.sh"
BRANDING = REPO_ROOT / "scripts" / "check_branding_and_notice.sh"

SLOTS = tuple(str(n) for n in range(1, 10))
SECTIONS = (
    "## Mission",
    "## Responsibilities",
    "## Allowed tools",
    "## Inputs",
    "## Outputs",
    "## Evidence policy",
    "## Context budget",
    "## Quality rubric",
    "## Escalation rules",
    "## Budget limit",
)


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def build_charters(
    root: Path,
    *,
    slots: tuple[str, ...] = SLOTS,
    sections: tuple[str, ...] = SECTIONS,
) -> Path:
    agents = root / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "agent-charters.txt").write_text(
        "".join(f"{slot} charter-{slot}.md\n" for slot in slots),
        encoding="utf-8",
    )
    body = "\n".join(sections) + "\n"
    for slot in slots:
        (agents / f"charter-{slot}.md").write_text(body, encoding="utf-8")
    return agents


class AgentCharterCheckTests(unittest.TestCase):
    def test_a_complete_manifest_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run(CHARTERS, str(build_charters(Path(tmp))))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("9 chartered agents", result.stdout)

    def test_missing_directory_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run(CHARTERS, str(Path(tmp) / "agents"))
            self.assertEqual(result.returncode, 1)
            self.assertIn("docs/agents/ is missing", result.stderr)

    def test_missing_charter_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agents = build_charters(Path(tmp))
            (agents / "charter-9.md").unlink()
            result = run(CHARTERS, str(agents))
            self.assertEqual(result.returncode, 1)
            self.assertIn("charter for slot 9 is missing", result.stderr)

    def test_charter_missing_a_section_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agents = build_charters(Path(tmp), sections=SECTIONS[:-1])
            result = run(CHARTERS, str(agents))
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing required section '## Budget limit'", result.stderr)

    def test_duplicate_slot_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agents = build_charters(Path(tmp))
            manifest = agents / "agent-charters.txt"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + "1 charter-1.md\n",
                encoding="utf-8",
            )
            result = run(CHARTERS, str(agents))
            self.assertEqual(result.returncode, 1)
            self.assertIn("duplicate slot '1'", result.stderr)

    def test_repository_charters_are_honest(self) -> None:
        # SPEC.md section 5 requires a charter for every agent; the nine core
        # agents plus the two capability slots must all be declared and complete.
        agents = REPO_ROOT / "docs" / "agents"
        result = run(CHARTERS, str(agents))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("11 chartered agents", result.stdout)

    def test_repository_branding_and_notice_are_honest(self) -> None:
        result = run(
            BRANDING,
            str(REPO_ROOT / "frontend"),
            str(REPO_ROOT / "vendor" / "openexecutive"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("branding/notice ok", result.stdout)

    def test_missing_vendored_notice_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frontend = root / "frontend"
            (frontend / "src" / "app").mkdir(parents=True)
            (frontend / "src" / "app" / "layout.tsx").write_text(
                "RED Operations Director\n", encoding="utf-8"
            )
            vendor = root / "vendor"
            vendor.mkdir()
            (vendor / "LICENSE").write_text("license\n", encoding="utf-8")
            result = run(BRANDING, str(frontend), str(vendor))
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing a non-empty NOTICE", result.stderr)

    def test_wrong_director_name_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frontend = root / "frontend"
            (frontend / "src" / "app").mkdir(parents=True)
            (frontend / "src" / "app" / "layout.tsx").write_text(
                "Chief Executive\n", encoding="utf-8"
            )
            vendor = root / "vendor"
            vendor.mkdir()
            (vendor / "LICENSE").write_text("license\n", encoding="utf-8")
            (vendor / "NOTICE").write_text("notice\n", encoding="utf-8")
            result = run(BRANDING, str(frontend), str(vendor))
            self.assertEqual(result.returncode, 1)
            self.assertIn("not named RED", result.stderr)


if __name__ == "__main__":
    unittest.main()

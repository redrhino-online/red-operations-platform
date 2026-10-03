"""Behavioral tests for the section 8 screen coverage gate.

SPEC.md section 13 condition 6 is "All section 8 screens render". The DoD
script's first cut passed on ``frontend/`` merely existing, so a screens-less
shell could falsely turn ``make done`` green and stop the build loop. These
tests pin the stricter contract in ``scripts/check_frontend_screens.sh``: the
frontend declares each section 8 screen and its route in
``frontend/dod-screens.txt``, every declared route resolves to a page, and a
browser test suite exists.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK = REPO_ROOT / "scripts" / "check_frontend_screens.sh"

SCREENS = (
    "portfolio-command-center",
    "client-workspace-overview",
    "source-and-claim-explorer",
    "transformation-map",
    "offer-and-journey-editor",
    "build-board",
    "approval-inbox",
    "workflow-run-detail",
    "launch-readiness",
    "performance-review",
    "portfolio-opportunities",
    "authority-settings",
)

ROUTE = {
    screen: f"/{screen}" for screen in SCREENS
}


def run_check(frontend: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CHECK), str(frontend)],
        capture_output=True,
        text=True,
        check=False,
    )


def build_frontend(
    root: Path,
    *,
    screens: tuple[str, ...] = SCREENS,
    page_for: tuple[str, ...] = SCREENS,
    browser_spec: bool = True,
) -> Path:
    frontend = root / "frontend"
    manifest = frontend / "dod-screens.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "".join(f"{screen} {ROUTE[screen]}\n" for screen in screens),
        encoding="utf-8",
    )
    for screen in page_for:
        page = frontend / "src" / "app" / screen / "page.tsx"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("export default function Page() {}\n", encoding="utf-8")
    if browser_spec:
        spec = frontend / "tests" / "screens.spec.ts"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text("test('screens', () => {});\n", encoding="utf-8")
    return frontend


class FrontendScreensCheckTests(unittest.TestCase):
    def test_a_complete_frontend_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frontend = build_frontend(Path(tmp))
            result = run_check(frontend)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("12 section 8 screens", result.stdout)

    def test_missing_frontend_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_check(Path(tmp) / "frontend")
            self.assertEqual(result.returncode, 1)
            self.assertIn("frontend/ is missing", result.stderr)

    def test_missing_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frontend = Path(tmp) / "frontend"
            frontend.mkdir()
            result = run_check(frontend)
            self.assertEqual(result.returncode, 1)
            self.assertIn("dod-screens.txt", result.stderr)

    def test_undeclared_screen_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frontend = build_frontend(Path(tmp), screens=SCREENS[:-1])
            result = run_check(frontend)
            self.assertEqual(result.returncode, 1)
            self.assertIn("authority-settings", result.stderr)

    def test_declared_screen_without_page_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frontend = build_frontend(Path(tmp), page_for=SCREENS[:-1])
            result = run_check(frontend)
            self.assertEqual(result.returncode, 1)
            self.assertIn("no page for screen 'authority-settings'", result.stderr)

    def test_missing_browser_suite_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frontend = build_frontend(Path(tmp), browser_spec=False)
            result = run_check(frontend)
            self.assertEqual(result.returncode, 1)
            self.assertIn("no browser test suite", result.stderr)

    def test_root_route_page_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            frontend = build_frontend(Path(tmp))
            manifest = frontend / "dod-screens.txt"
            manifest.write_text(
                "\n".join(
                    f"{screen} {'/' if screen == 'portfolio-command-center' else ROUTE[screen]}"
                    for screen in SCREENS
                )
                + "\n",
                encoding="utf-8",
            )
            root_page = frontend / "src" / "app" / "page.tsx"
            root_page.write_text("export default function Page() {}\n", encoding="utf-8")
            result = run_check(frontend)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

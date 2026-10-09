"""Behavioral tests for the section 8 screen coverage gate.

SPEC.md section 13 condition 6 is "All section 8 screens render". Since the
single-shell overhaul (SPEC.md section 14, ADR 0013) the cockpit is the only
user-facing UI, so the gate exercises the native ``/operations/*`` cockpit pages
rather than the retired ``/screens`` thin client. These tests pin the contract in
``scripts/check_frontend_screens.sh``: a repo-side manifest declares each section
8 screen and its native route, every declared route resolves to a cockpit page,
and a component test suite exists.
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
    "portfolio-command-center": "/operations/command-center",
    "client-workspace-overview": "/operations/client-workspace",
    "source-and-claim-explorer": "/operations/source-explorer",
    "transformation-map": "/operations/transformation-map",
    "offer-and-journey-editor": "/operations/offer-and-journey",
    "build-board": "/operations/build-board",
    "approval-inbox": "/operations/approval-inbox",
    "workflow-run-detail": "/operations/workflow-run-detail",
    "launch-readiness": "/operations/launch-readiness",
    "performance-review": "/operations/performance-review",
    "portfolio-opportunities": "/operations/portfolio-opportunities",
    "authority-settings": "/operations/authority-settings",
}


def run_check(cockpit: Path, manifest: Path, test_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CHECK), str(cockpit), str(manifest), str(test_dir)],
        capture_output=True,
        text=True,
        check=False,
    )


def build_cockpit(
    root: Path,
    *,
    screens: tuple[str, ...] = SCREENS,
    page_for: tuple[str, ...] = SCREENS,
    component_suite: bool = True,
) -> tuple[Path, Path, Path]:
    cockpit = root / "cockpit"
    manifest = root / "dod-screens.txt"
    manifest.write_text(
        "".join(f"{screen} {ROUTE[screen]}\n" for screen in screens),
        encoding="utf-8",
    )
    for screen in page_for:
        rel = ROUTE[screen].lstrip("/")
        page = cockpit / "src" / "app" / rel / "page.tsx"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("export default function Page() {}\n", encoding="utf-8")
    test_dir = root / "tests" / "cockpit-ui"
    test_dir.mkdir(parents=True, exist_ok=True)
    if component_suite:
        (test_dir / "screens.test.tsx").write_text(
            "test('screens', () => {});\n", encoding="utf-8"
        )
    return cockpit, manifest, test_dir


class CockpitScreensCheckTests(unittest.TestCase):
    def test_a_complete_cockpit_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cockpit, manifest, test_dir = build_cockpit(Path(tmp))
            result = run_check(cockpit, manifest, test_dir)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("12 section 8 screens", result.stdout)

    def test_missing_cockpit_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, manifest, test_dir = build_cockpit(root)
            result = run_check(root / "missing", manifest, test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("is missing", result.stderr)

    def test_missing_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cockpit, _, test_dir = build_cockpit(root)
            result = run_check(cockpit, root / "missing.txt", test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing", result.stderr)

    def test_undeclared_screen_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cockpit, manifest, test_dir = build_cockpit(
                Path(tmp), screens=SCREENS[:-1]
            )
            result = run_check(cockpit, manifest, test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("authority-settings", result.stderr)

    def test_declared_screen_without_page_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cockpit, manifest, test_dir = build_cockpit(
                Path(tmp), page_for=SCREENS[:-1]
            )
            result = run_check(cockpit, manifest, test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("no cockpit page for screen 'authority-settings'", result.stderr)

    def test_non_native_route_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cockpit, manifest, test_dir = build_cockpit(root)
            manifest.write_text(
                "".join(
                    f"{screen} {'/screens/' + screen if screen == 'build-board' else ROUTE[screen]}\n"
                    for screen in SCREENS
                ),
                encoding="utf-8",
            )
            result = run_check(cockpit, manifest, test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("/operations/", result.stderr)

    def test_missing_component_suite_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cockpit, manifest, test_dir = build_cockpit(
                Path(tmp), component_suite=False
            )
            result = run_check(cockpit, manifest, test_dir)
            self.assertEqual(result.returncode, 1)
            self.assertIn("no component test suite", result.stderr)


if __name__ == "__main__":
    unittest.main()

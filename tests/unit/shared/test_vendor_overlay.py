"""Behavioral tests for the re-triggerable vendor overlay (ADR 0011).

SPEC.md section 13 condition 7 requires every local change to the vendored
OpenExecutive to be overlay-declared and reproducible from this repository. These
tests pin the overlay contract: apply is idempotent, check passes on an applied
tree and fails on an unaccounted vendor change, and apply fails loudly when an
upstream change moves a hook anchor. The real repository is checked too, so the
committed overlay and the applied submodule cannot drift.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
APPLY_SH = REPO_ROOT / "scripts" / "apply_vendor_overlay.sh"

_spec = importlib.util.spec_from_file_location(
    "vendor_overlay", REPO_ROOT / "scripts" / "vendor_overlay.py"
)
vendor_overlay = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(vendor_overlay)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def build_fixture(root: Path) -> Path:
    vendor = root / "vendor" / "openexecutive"
    (vendor / "orchestrator").mkdir(parents=True)
    (vendor / "orchestrator" / "router.py").write_text(
        "REGISTRY = {}\n", encoding="utf-8"
    )
    _git(vendor, "init", "-q")
    _git(vendor, "config", "user.email", "test@example.com")
    _git(vendor, "config", "user.name", "Test")
    _git(vendor, "add", "-A")
    _git(vendor, "commit", "-qm", "pinned upstream")

    files = root / "vendor" / "overlay" / "files" / "pkg"
    files.mkdir(parents=True)
    (files / "new_module.py").write_text("VALUE = 1\n", encoding="utf-8")

    hooks = root / "vendor" / "overlay" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "router.py.snippet").write_text("REGISTRY['red'] = 1\n", encoding="utf-8")
    (hooks / "manifest.txt").write_text(
        "orchestrator/router.py router.py.snippet red-reg\n", encoding="utf-8"
    )
    return root


class VendorOverlayTests(unittest.TestCase):
    def test_apply_then_check_passes_and_reapply_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(Path(tmp))
            changed = vendor_overlay.apply(root)
            self.assertIn("pkg/new_module.py", changed)
            self.assertIn("orchestrator/router.py", changed)
            vendor_overlay.check(root)
            self.assertEqual([], vendor_overlay.apply(root))
            self.assertIn(
                "# RED-OVERLAY:BEGIN red-reg",
                (root / "vendor/openexecutive/orchestrator/router.py").read_text(),
            )

    def test_check_fails_on_an_unaccounted_vendor_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(Path(tmp))
            vendor_overlay.apply(root)
            (root / "vendor/openexecutive/orchestrator/rogue.py").write_text(
                "x = 1\n", encoding="utf-8"
            )
            with self.assertRaises(vendor_overlay.OverlayError):
                vendor_overlay.check(root)

    def test_check_fails_when_the_overlay_is_not_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(Path(tmp))
            with self.assertRaises(vendor_overlay.OverlayError):
                vendor_overlay.check(root)

    def test_apply_fails_when_an_upstream_change_moved_a_hook_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(Path(tmp))
            (root / "vendor/openexecutive/orchestrator/router.py").unlink()
            with self.assertRaises(vendor_overlay.OverlayError):
                vendor_overlay.apply(root)

    def test_reapply_refreshes_the_hook_block_after_an_upstream_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = build_fixture(Path(tmp))
            vendor_overlay.apply(root)
            router = root / "vendor/openexecutive/orchestrator/router.py"
            router.write_text(router.read_text().replace(" 1\n", " 2\n"))
            self.assertEqual(["orchestrator/router.py"], vendor_overlay.apply(root))
            vendor_overlay.check(root)

    def test_the_real_repository_overlay_is_applied_and_declared(self) -> None:
        result = subprocess.run(
            ["bash", str(APPLY_SH), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("vendor overlay check ok", result.stdout)


if __name__ == "__main__":
    unittest.main()

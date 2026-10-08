"""Behavioral tests for the absorbed-fork additive gate.

ADR 0014 absorbs the OpenExecutive fork into this repository. RED changes inside
`vendor/openexecutive/` are additive by default: red-owned surfaces
(`vendor/red-owned-files.txt`) and new files stay freely editable, while every
other upstream-origin file (`vendor/upstream-files.txt`) is locked to the bytes
baselined in `vendor/upstream-manifest.sha256`. These tests pin both modes of
`scripts/vendor_pin.py` and the `scripts/check_vendor_additive.sh` gate: a
modified locked file fails, a modified red-owned file passes, a new file passes,
and a deliberate re-pin re-baselines.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECK = REPO_ROOT / "scripts" / "check_vendor_additive.sh"
PIN = REPO_ROOT / "scripts" / "vendor_pin.py"


def run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    return subprocess.run(
        ["bash", str(script), *args] if script.suffix == ".sh" else ["python3", str(script), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def build_repo(root: Path) -> tuple[Path, dict[str, bytes]]:
    repo = root / "repo"
    vend = repo / "vendor" / "openexecutive"
    files = {
        "upstream/a.txt": b"upstream a\n",
        "upstream/b.txt": b"upstream b\n",
        "upstream/deep/c.txt": b"upstream c\n",
        "red-owned/nav.ts": b"RED nav\n",
    }
    for rel, data in files.items():
        path = vend / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    (repo / "vendor" / "upstream-files.txt").write_text(
        "upstream/a.txt\nupstream/b.txt\nupstream/deep/c.txt\nred-owned/nav.ts\n",
        encoding="utf-8",
    )
    (repo / "vendor" / "red-owned-files.txt").write_text(
        "red-owned/nav.ts\n", encoding="utf-8"
    )
    manifest_lines = [
        f"{hashlib.sha256(data).hexdigest()}  {rel}"
        for rel, data in files.items()
        if not rel.startswith("red-owned/")
    ]
    (repo / "vendor" / "upstream-manifest.sha256").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )
    return repo, files


class VendorAdditiveCheckTests(unittest.TestCase):
    def test_passes_when_locked_files_match_the_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = build_repo(Path(tmp))
            result = run(CHECK, str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("vendor-additive ok", result.stdout)

    def test_passes_when_a_new_additive_file_is_added(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = build_repo(Path(tmp))
            page = repo / "vendor" / "openexecutive" / "packages" / "ui" / "src" / "app" / "operations" / "command-center" / "page.tsx"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text("export default () => null;\n", encoding="utf-8")
            result = run(CHECK, str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_fails_when_a_locked_file_is_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = build_repo(Path(tmp))
            locked = repo / "vendor" / "openexecutive" / "upstream" / "b.txt"
            locked.write_bytes(b"tampered\n", )
            result = run(CHECK, str(repo))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("modified locked file", result.stderr)
            self.assertIn("upstream/b.txt", result.stderr)

    def test_fails_when_a_locked_file_is_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = build_repo(Path(tmp))
            (repo / "vendor" / "openexecutive" / "upstream" / "deep" / "c.txt").unlink()
            result = run(CHECK, str(repo))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing locked file", result.stderr)

    def test_passes_when_a_red_owned_file_is_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = build_repo(Path(tmp))
            red = repo / "vendor" / "openexecutive" / "red-owned" / "nav.ts"
            red.write_bytes(b"RED nav, restyled\n", )
            result = run(CHECK, str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_fails_without_a_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = build_repo(Path(tmp))
            (repo / "vendor" / "upstream-manifest.sha256").unlink()
            result = run(CHECK, str(repo))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("upstream-manifest.sha256 is missing", result.stderr)

    def test_pin_rebaselines_and_check_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = build_repo(Path(tmp))
            locked = repo / "vendor" / "openexecutive" / "upstream" / "a.txt"
            locked.write_bytes(b"owner-approved change\n")
            self.assertNotEqual(run(CHECK, str(repo)).returncode, 0)

            result = run(PIN, "pin", "--repo", str(repo))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("baselined 3 locked files", result.stdout)

            recovered = run(CHECK, str(repo))
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            manifest = (repo / "vendor" / "upstream-manifest.sha256").read_text(encoding="utf-8")
            self.assertIn(hashlib.sha256(b"owner-approved change\n").hexdigest(), manifest)

    def test_pin_refuses_red_owned_files_outside_the_upstream_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = build_repo(Path(tmp))
            extra = repo / "vendor" / "red-owned-files.txt"
            extra.write_text("red-owned/nav.ts\nnot/upstream.txt\n", encoding="utf-8")
            result = run(PIN, "pin", "--repo", str(repo))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the upstream tree", result.stderr)


if __name__ == "__main__":
    unittest.main()

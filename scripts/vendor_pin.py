#!/usr/bin/env python3
"""Baseline and verify the absorbed OpenExecutive fork (ADR 0014).

The fork is absorbed into this repository at a pinned upstream commit. RED
changes inside ``vendor/openexecutive/`` are additive by default; the files the
RED adoption already modified or added at absorption (``vendor/red-owned-files.txt``)
stay freely editable, and every other upstream-origin file
(``vendor/upstream-files.txt``) is locked to the bytes recorded in
``vendor/upstream-manifest.sha256``.

Modes:
  --pin    Re-baseline the manifest from the current tree. Owner action only:
           run it after an owner-approved exception recorded in
           ``docs/fork_inventory.md`` or after an upstream merge. Unattended
           build cycles never pin.
  --check  Verify only: every locked file must still match its recorded hash.
           Missing files fail. Extra (additive or red-owned) files are
           unrestricted and ignored.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

VENDOR = "vendor/openexecutive"
UPSTREAM_FILES = "vendor/upstream-files.txt"
RED_OWNED_FILES = "vendor/red-owned-files.txt"
MANIFEST = "vendor/upstream-manifest.sha256"


def locked_paths(repo: Path) -> list[str]:
    upstream = [p for p in (repo / UPSTREAM_FILES).read_text(encoding="utf-8").splitlines() if p]
    red_owned = {p for p in (repo / RED_OWNED_FILES).read_text(encoding="utf-8").splitlines() if p}
    # Red-owned paths outside the upstream tree are RED-added files (they were
    # never upstream-origin), so they cannot be locked; warn, don't fail.
    outside = sorted(red_owned - set(upstream))
    if outside:
        print(
            f"vendor-pin: note: {len(outside)} red-owned entries are RED-added "
            "files absent from the upstream tree (not lockable): "
            f"{outside[:3]}{'…' if len(outside) > 3 else ''}",
            file=sys.stderr,
        )
    return [p for p in upstream if p not in red_owned]


def read_manifest(repo: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in (repo / MANIFEST).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, path = line.partition("  ")
        entries[path.strip()] = digest.strip()
    return entries


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pin(repo: Path) -> None:
    lines = [f"{digest(repo / VENDOR / p)}  {p}" for p in locked_paths(repo)]
    (repo / MANIFEST).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"vendor-pin: baselined {len(lines)} locked files into {MANIFEST}")


def check(repo: Path) -> int:
    vend = repo / VENDOR
    manifest = read_manifest(repo)
    if not manifest:
        print(f"vendor-pin: {MANIFEST} is empty; pin the absorbed fork first")
        return 1

    failures: list[str] = []
    for path, expected in manifest.items():
        file_path = vend / path
        if not file_path.is_file():
            failures.append(f"missing locked file: {VENDOR}/{path}")
        elif digest(file_path) != expected:
            failures.append(f"modified locked file: {VENDOR}/{path}")

    if failures:
        for line in failures:
            print(f"VENDOR-ADDITIVE FAIL: {line}", file=sys.stderr)
        print(
            "vendor-pin: locked upstream-origin files must stay additive-stable "
            "(ADR 0014); an owner-approved exception recorded in "
            "docs/fork_inventory.md followed by `make vendor-pin` is the only "
            "sanctioned way to change them",
            file=sys.stderr,
        )
        return 1

    print(f"vendor-additive ok: {len(manifest)} locked files match the baseline")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    repo_dir = Path(__file__).resolve().parent.parent
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("check", "pin"),
        default="check",
        help="check (default) verifies the baseline; pin re-baselines it",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=repo_dir,
        help="repository root (defaults to the script's parent directory)",
    )
    args = parser.parse_args()
    repo = args.repo.resolve()
    for required in (UPSTREAM_FILES, RED_OWNED_FILES):
        if not (repo / required).is_file():
            raise SystemExit(f"vendor_pin: missing {required} (the fork is not absorbed yet)")
    if args.mode == "pin":
        pin(repo)
    else:
        raise SystemExit(check(repo))


if __name__ == "__main__":
    main()

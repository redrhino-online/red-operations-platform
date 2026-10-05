#!/usr/bin/env python3
"""Apply or verify the committed RED vendor overlay (ADR 0011).

The vendored OpenExecutive submodule is a pinned dependency (ADR 0008). Where
the fork's own specialist mechanism requires in-package artifacts (ADR 0006,
queue Q3), RED edits the submodule only through this overlay: RED-authored files
live in this repository under ``vendor/overlay/`` and are applied onto
``vendor/openexecutive/`` idempotently. Re-running ``apply`` is a no-op; after an
upstream submodule bump it re-applies the same overlay onto the new commit.

Two kinds of overlay artifact:

* Files under ``vendor/overlay/files/<path>`` are copied verbatim onto
  ``vendor/openexecutive/<path>``.
* Hook snippets are spliced into an existing vendor file between explicit
  ``# RED-OVERLAY:BEGIN <marker>`` / ``# RED-OVERLAY:END <marker>`` markers, so
  apply replaces its own block instead of appending a duplicate. The hook
  manifest is ``vendor/overlay/hooks/manifest.txt`` with one line per hook:
  ``<target-relative-path> <snippet-file> <marker>``.

``check`` proves the vendor working tree equals the overlay applied onto the
pinned commit and that no tracked or untracked vendor change falls outside the
overlay. It fails loudly when an upstream change moves a hook anchor.

Usage: vendor_overlay.py [apply|check] [repo-root]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BEGIN = "# RED-OVERLAY:BEGIN {marker}"
END = "# RED-OVERLAY:END {marker}"


class OverlayError(RuntimeError):
    """The overlay cannot be applied or the vendor tree diverges."""


def _repo_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    return Path(__file__).resolve().parent.parent


def _read_manifest(hooks_dir: Path) -> list[tuple[str, str, str]]:
    manifest = hooks_dir / "manifest.txt"
    if not manifest.is_file():
        raise OverlayError(f"missing hook manifest: {manifest}")
    hooks: list[tuple[str, str, str]] = []
    for lineno, raw in enumerate(manifest.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise OverlayError(
                f"{manifest}:{lineno}: expected '<target> <snippet> <marker>', got {raw!r}"
            )
        hooks.append((parts[0], parts[1], parts[2]))
    return hooks


def _overlay_file_targets(files_dir: Path) -> list[Path]:
    if not files_dir.is_dir():
        # An overlay may carry only hooks; a missing files/ tree is empty, not an
        # error, so the mechanism can land before its content.
        return []
    return sorted(p for p in files_dir.rglob("*") if p.is_file())


def _desired_block(snippet_text: str, marker: str) -> str:
    begin = BEGIN.format(marker=marker)
    end = END.format(marker=marker)
    body = snippet_text.rstrip("\n")
    return f"{begin}\n{body}\n{end}\n"


def _spliced_text(target_text: str, desired: str, marker: str, target: Path) -> str:
    begin = BEGIN.format(marker=marker)
    end = END.format(marker=marker)
    if begin in target_text or end in target_text:
        start = target_text.find(begin)
        stop = target_text.find(end)
        if start == -1 or stop == -1:
            raise OverlayError(
                f"{target}: has only one of the {begin!r}/{end!r} markers; "
                "the vendor file was edited outside the overlay"
            )
        stop += len(end)
        # Consume the newline that terminates the end marker, if present.
        if stop < len(target_text) and target_text[stop] == "\n":
            stop += 1
        return target_text[:start] + desired + target_text[stop:]
    separator = "" if target_text.endswith("\n\n") else ("\n" if target_text.endswith("\n") else "\n\n")
    return target_text + separator + desired


def _status_paths(root: Path) -> set[str]:
    vendor = root / "vendor" / "openexecutive"
    proc = subprocess.run(
        ["git", "-C", str(vendor), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise OverlayError(
            "could not read vendor/openexecutive git status: " + proc.stderr.strip()
        )
    paths: set[str] = set()
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths


def _expected_vendor_paths(root: Path) -> set[str]:
    files_dir = root / "vendor" / "overlay" / "files"
    hooks_dir = root / "vendor" / "overlay" / "hooks"
    expected = {p.relative_to(files_dir).as_posix() for p in _overlay_file_targets(files_dir)}
    expected.update(target for target, _, _ in _read_manifest(hooks_dir))
    return expected


def apply(root: Path) -> list[str]:
    """Copy overlay files and splice hook blocks. Idempotent; returns changed paths."""
    files_dir = root / "vendor" / "overlay" / "files"
    hooks_dir = root / "vendor" / "overlay" / "hooks"
    vendor = root / "vendor" / "openexecutive"
    if not vendor.is_dir():
        raise OverlayError(
            "vendor/openexecutive is missing; run `git submodule update --init` first"
        )
    changed: list[str] = []

    for source in _overlay_file_targets(files_dir):
        rel = source.relative_to(files_dir)
        target = vendor / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        desired = source.read_bytes()
        if not target.is_file() or target.read_bytes() != desired:
            target.write_bytes(desired)
            changed.append(rel.as_posix())

    for target_rel, snippet_name, marker in _read_manifest(hooks_dir):
        target = vendor / target_rel
        if not target.is_file():
            raise OverlayError(
                f"hook target missing: {target_rel}; an upstream change moved it, "
                "so the overlay must be fixed before it can be applied"
            )
        snippet = (hooks_dir / snippet_name).read_text()
        desired = _desired_block(snippet, marker)
        current = target.read_text()
        updated = _spliced_text(current, desired, marker, target)
        if updated != current:
            target.write_text(updated)
            changed.append(target_rel)

    return changed


def check(root: Path) -> None:
    """Verify the vendor tree equals the overlay applied; raise on divergence."""
    files_dir = root / "vendor" / "overlay" / "files"
    hooks_dir = root / "vendor" / "overlay" / "hooks"
    vendor = root / "vendor" / "openexecutive"

    for source in _overlay_file_targets(files_dir):
        rel = source.relative_to(files_dir)
        target = vendor / rel
        if not target.is_file():
            raise OverlayError(f"overlay file not applied: {rel.as_posix()}")
        if target.read_bytes() != source.read_bytes():
            raise OverlayError(
                f"overlay file diverges from vendor: {rel.as_posix()} "
                "(run scripts/apply_vendor_overlay.sh)"
            )

    for target_rel, snippet_name, marker in _read_manifest(hooks_dir):
        target = vendor / target_rel
        if not target.is_file():
            raise OverlayError(f"hook target missing: {target_rel}")
        snippet = (hooks_dir / snippet_name).read_text()
        desired = _desired_block(snippet, marker)
        if desired not in target.read_text():
            raise OverlayError(
                f"hook block for {marker!r} is missing or stale in {target_rel} "
                "(run scripts/apply_vendor_overlay.sh)"
            )

    expected = _expected_vendor_paths(root)
    actual = _status_paths(root)
    unaccounted = sorted(actual - expected)
    if unaccounted:
        raise OverlayError(
            "vendor/openexecutive has changes outside the overlay: "
            + ", ".join(unaccounted)
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("apply", "check"))
    parser.add_argument("repo_root", nargs="?", default=None)
    args = parser.parse_args(argv)
    root = _repo_root(args.repo_root)
    try:
        if args.action == "apply":
            changed = apply(root)
            if changed:
                print("vendor overlay applied: " + ", ".join(changed))
            else:
                print("vendor overlay already applied: no changes")
        else:
            check(root)
            print("vendor overlay check ok: vendor tree equals the committed overlay")
    except OverlayError as exc:
        print(f"vendor overlay error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Seed the pinned reference canon into the cockpit Knowledge (K9; SPEC.md
sections 12 and 14 condition 6).

The 2026-10-07 canon ingestion was a manual one-off. This seed makes it
verifiable and repeatable: it recomputes the canon content hash with the same
algorithm ``scripts/canon_hash.sh`` pins into ``canon.lock`` and refuses to run
when the canon has drifted, then ingests every canon ``.txt``/``.md`` file into
the cockpit Knowledge domain ``redops-canon`` through the vendored loader's
ingest seam — the same ``ingest_text_sync`` call ``POST /documents`` makes — so
the corpus is retrievable by the same unfiltered company-docs query every
specialist reads. Chunk ids are derived from the canon-relative source name and
chunk index, so a rerun upserts the same ids and changes nothing.

Canon material is data, never instructions (SPEC.md section 12.2): the seed
stores it for retrieval and copies no canon text into a prompt or artifact. The
trees the canon hash excludes (``.git``, ``.venv``, ``site``) are excluded here
too, so the seeded corpus is exactly the pinned content.

Usage: ``make seed-canon`` (``python -m redops.seed_canon``) reads the canon
root from ``RALPH_CANON`` (default: the sibling ``canon/`` directory) and the
vector store from ``VECTOR_STORE_PATH``. It approves nothing, spends nothing and
deploys nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from openexecutive.knowledge.loader import REDOPS_CANON_DOMAIN, ingest_text_sync
from openexecutive.knowledge.store import ChromaDBStore

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCK_PATH = REPO_ROOT / "canon.lock"
CANON_SUFFIXES = frozenset({".txt", ".md"})
# The trees scripts/canon_hash.sh excludes from the pinned content.
EXCLUDED_TOP_LEVEL = frozenset({".git", ".venv", "site"})


class CanonPinDriftError(RuntimeError):
    """The canon content no longer matches the pinned hash in canon.lock."""


def canon_files(canon_root: Path) -> list[Path]:
    """The canon corpus files, exactly the set the pinned hash covers."""

    files: list[Path] = []
    for path in sorted(canon_root.rglob("*")):
        if not path.is_file() or path.suffix not in CANON_SUFFIXES:
            continue
        relative = path.relative_to(canon_root)
        if relative.parts and relative.parts[0] in EXCLUDED_TOP_LEVEL:
            continue
        files.append(path)
    return files


def canon_content_hash(canon_root: Path) -> str:
    """The canon content hash, byte-identical to ``scripts/canon_hash.sh``.

    The script hashes each canon file, prints ``<digest>  ./<path>`` lines in
    LC_ALL=C path order and hashes that stream; this replicates it so the seed
    verifies against the same pin the harness wrote.
    """

    entries: list[tuple[str, str]] = []
    for path in canon_files(canon_root):
        relative = "./" + path.relative_to(canon_root).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        entries.append((relative, digest))
    entries.sort(key=lambda entry: entry[0].encode())
    stream = "".join(f"{digest}  {relative}\n" for relative, digest in entries)
    return hashlib.sha256(stream.encode()).hexdigest()


def read_pinned_hash(lock_path: Path) -> str | None:
    """The pinned hash from ``canon.lock`` (first field of the first line)."""

    if not lock_path.exists():
        return None
    first = lock_path.read_text(encoding="utf-8").splitlines()[0].strip()
    return first.split()[0] if first else None


def verify_canon_pin(canon_root: Path, lock_path: Path | None) -> str:
    """Refuse to seed a canon that drifted from its pin; return the actual hash."""

    digest = canon_content_hash(canon_root)
    if lock_path is None:
        return digest
    pinned = read_pinned_hash(lock_path)
    if pinned is None:
        raise CanonPinDriftError(
            f"canon.lock is missing or empty at {lock_path}; the seed is only "
            "verifiable over a pinned canon"
        )
    if pinned != digest:
        raise CanonPinDriftError(
            f"canon content drifted from the pin: pinned {pinned}, actual {digest}; "
            "re-pin with make canon-pin before seeding"
        )
    return digest


def seed_canon_knowledge(
    canon_root: Path,
    store: ChromaDBStore,
    *,
    lock_path: Path | None = DEFAULT_LOCK_PATH,
) -> dict[str, int]:
    """Ingest the pinned canon corpus into the ``redops-canon`` domain.

    Every canon file is indexed under its canon-relative path as the chunk-id
    namespace, so a rerun upserts the same ids and the collection neither grows
    nor changes. Returns the file and chunk counts.
    """

    verify_canon_pin(canon_root, lock_path)
    files = canon_files(canon_root)
    chunks = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        chunks += ingest_text_sync(
            text,
            store,
            source_name=path.relative_to(canon_root).as_posix(),
            domain=REDOPS_CANON_DOMAIN,
            collection=ChromaDBStore.COMPANY_COLLECTION,
            extra_metadata={"canon": "true"},
        )
    return {"files": len(files), "chunks": chunks}


def canon_root_from_env() -> Path:
    """The canon root: ``RALPH_CANON`` or the sibling ``canon/`` directory."""

    raw = os.environ.get("RALPH_CANON")
    if raw:
        return Path(raw)
    return REPO_ROOT.parent / "canon"


def seed_canon_from_env() -> dict[str, int]:
    """Seed the canon named by the environment into its vector store."""

    store = ChromaDBStore(
        persist_directory=os.environ.get("VECTOR_STORE_PATH", "./chroma_db")
    )
    return seed_canon_knowledge(
        canon_root_from_env(), store, lock_path=DEFAULT_LOCK_PATH
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the pinned canon into Knowledge (K9).")
    parser.add_argument(
        "--canon",
        type=Path,
        default=None,
        help="Canon root (default: RALPH_CANON or the sibling canon/ directory)",
    )
    parser.add_argument(
        "--vector-store",
        type=Path,
        default=None,
        help="ChromaDB persist directory (default: VECTOR_STORE_PATH or ./chroma_db)",
    )
    args = parser.parse_args()
    canon_root = args.canon or canon_root_from_env()
    store = ChromaDBStore(
        persist_directory=args.vector_store or os.environ.get("VECTOR_STORE_PATH", "./chroma_db")
    )
    summary = seed_canon_knowledge(canon_root, store, lock_path=DEFAULT_LOCK_PATH)
    print(f"canon seed: {summary['files']} files, {summary['chunks']} chunks indexed")


if __name__ == "__main__":
    main()

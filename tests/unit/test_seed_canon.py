"""Behavioral tests for the K9 canon-into-Knowledge seed.

Item K9 (IMPLEMENTATION_PLAN.md) turns the manual canon ingestion into a
verifiable, idempotent seed over the pinned canon: the seed refuses to run when
the canon content no longer matches ``canon.lock``, ingests the canon corpus
into the cockpit Knowledge domain ``redops-canon`` through the vendored loader's
ingest seam (the same one ``POST /documents`` uses), and a rerun changes
nothing. SPEC.md section 14 condition 6 requires the canon corpus ingested
repeatably and an eval scenario asserting an answer grounds on canon files.

The tests skip cleanly when the vendored ``openexecutive`` package is not
importable.
"""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HAS_OPENEXECUTIVE = importlib.util.find_spec("openexecutive") is not None
SKIP_REASON = "the canon seed needs the vendored openexecutive package"
CANON_HASH_SCRIPT = REPO_ROOT / "scripts" / "canon_hash.sh"
COMPANY_COLLECTION = "company_docs"
CANON_DOMAIN = "redops-canon"


def build_canon(root: Path) -> Path:
    """A small canon with the three parts plus the trees the hash excludes."""

    (root / "framework-canon").mkdir(parents=True)
    (root / "docs" / "method").mkdir(parents=True)
    (root / "internal").mkdir(parents=True)
    (root / "framework-canon" / "00 - Getting Started.txt").write_text(
        "The program runs over twelve weeks and ends with a launched campaign.\n",
        encoding="utf-8",
    )
    (root / "docs" / "method" / "motions.md").write_text(
        "# The RED Method\n\nThree phases and nine motions carry the client from\n"
        "refine offer through develop audience.\n",
        encoding="utf-8",
    )
    (root / "internal" / "stations.md").write_text(
        "# Stations\n\nThe operator build line runs Plan, Market, Message.\n",
        encoding="utf-8",
    )
    # Trees the canon hash excludes must never enter the seed either.
    (root / "site").mkdir()
    (root / "site" / "index.md").write_text("built site\n", encoding="utf-8")
    (root / ".venv").mkdir()
    (root / ".venv" / "noise.md").write_text("venv noise\n", encoding="utf-8")
    return root


def script_hash(canon_root: Path) -> str:
    result = subprocess.run(
        ["bash", str(CANON_HASH_SCRIPT), str(canon_root)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def write_pin(canon_root: Path, lock_path: Path) -> str:
    digest = script_hash(canon_root)
    lock_path.write_text(f"{digest} 2026-10-10T00:00:00Z\n", encoding="utf-8")
    return digest


@unittest.skipUnless(HAS_OPENEXECUTIVE, SKIP_REASON)
class CanonSeedTests(unittest.TestCase):
    """The seed ingests the pinned canon once and a rerun changes nothing."""

    def setUp(self) -> None:
        from redops.seed_canon import seed_canon_knowledge

        self.seed = seed_canon_knowledge
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.canon = build_canon(self.root / "canon")
        self.lock = self.root / "canon.lock"
        self.store_dir = self.root / "chroma_db"

    def _store(self):
        from openexecutive.knowledge.store import ChromaDBStore

        return ChromaDBStore(persist_directory=self.store_dir)

    def _company_rows(self, store, query: str = "canon"):
        return store.query(
            query_text=query,
            collection=COMPANY_COLLECTION,
            domain_filter=None,
            n_results=50,
        )

    def test_python_hash_matches_the_canon_hash_script(self) -> None:
        from redops.seed_canon import canon_content_hash

        self.assertEqual(canon_content_hash(self.canon), script_hash(self.canon))

    def test_seeds_the_canon_corpus_into_the_redops_canon_domain(self) -> None:
        write_pin(self.canon, self.lock)
        summary = self.seed(self.canon, self._store(), lock_path=self.lock)

        self.assertEqual(summary["files"], 3)
        self.assertGreater(summary["chunks"], 0)
        rows = self._company_rows(self._store(), "twelve weeks program")
        sources = {row["metadata"]["source"] for row in rows}
        self.assertIn("framework-canon/00 - Getting Started.txt", sources)
        domains = {row["metadata"]["domain"] for row in rows}
        self.assertEqual(domains, {CANON_DOMAIN})
        # The built site and the venv noise are not canon content.
        self.assertNotIn("site/index.md", sources)
        self.assertNotIn(".venv/noise.md", sources)

    def test_rerun_changes_nothing(self) -> None:
        write_pin(self.canon, self.lock)
        store = self._store()
        first = self.seed(self.canon, store, lock_path=self.lock)
        before_count = store.get_collection_count(COMPANY_COLLECTION)
        before_rows = self._company_rows(store)

        second = self.seed(self.canon, store, lock_path=self.lock)

        self.assertEqual(second["files"], first["files"])
        self.assertEqual(second["chunks"], first["chunks"])
        self.assertEqual(store.get_collection_count(COMPANY_COLLECTION), before_count)
        self.assertEqual(self._company_rows(store), before_rows)

    def test_refuses_to_seed_a_canon_that_drifted_from_the_pin(self) -> None:
        write_pin(self.canon, self.lock)
        (self.canon / "docs" / "method" / "motions.md").write_text(
            "changed\n", encoding="utf-8"
        )

        with self.assertRaises(Exception) as ctx:
            self.seed(self.canon, self._store(), lock_path=self.lock)
        self.assertIn("canon", str(ctx.exception).lower())

    def test_canon_files_exclude_the_hash_excluded_trees(self) -> None:
        from redops.seed_canon import canon_files

        names = [p.relative_to(self.canon).as_posix() for p in canon_files(self.canon)]
        self.assertEqual(
            names,
            [
                "docs/method/motions.md",
                "framework-canon/00 - Getting Started.txt",
                "internal/stations.md",
            ],
        )


if __name__ == "__main__":
    unittest.main()

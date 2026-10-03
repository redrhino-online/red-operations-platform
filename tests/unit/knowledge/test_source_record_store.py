"""Behavioral tests for the source record store (Knowledge application).

Rules under test come from SPEC.md sections 3, 9 and 11:
- The original is immutable and retrievable to authorized users, so a same-key
  record with different contents is refused (SPEC.md section 3).
- A source record is a client resource: every read and write carries
  ``tenant_id``, and one client's sources cannot be read for another (sections 3
  and 9).
- Source attribution survives ingestion, so a reloaded record keeps its locator,
  checksum and capture time (section 11).

The durable PostgreSQL case skips cleanly when no psycopg, alembic or
``DATABASE_URL`` is present:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/knowledge/test_source_record_store.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.knowledge.domain.entities import SourceRecord
from redops.contexts.knowledge.domain.errors import (
    SourceRecordImmutableError,
    UnscopedSourceRecordError,
)
from redops.contexts.knowledge.infrastructure.mappers import (
    source_from_payload,
    source_to_payload,
)
from redops.contexts.knowledge.infrastructure.repositories import (
    InMemorySourceRecordStore,
)

TENANT = "3fmindset"
OTHER_TENANT = "client-other"
ON = date(2026, 10, 3)

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def source(
    source_id: str = "src-1",
    tenant_id: str = TENANT,
    checksum: str = "sha256:abc",
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        tenant_id=tenant_id,
        locator="project_sources/notes/01.md",
        checksum=checksum,
        captured_on=ON,
        access_rule="client-and-red-only",
    )


class InMemorySourceRecordStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemorySourceRecordStore()

    def test_a_saved_source_is_resolved_by_source_id(self) -> None:
        stored = source()

        self.store.save(stored)

        self.assertEqual(stored, self.store.get(TENANT, "src-1"))

    def test_an_unknown_source_resolves_to_none(self) -> None:
        self.store.save(source())

        self.assertIsNone(self.store.get(TENANT, "missing"))
        self.assertIsNone(self.store.get(OTHER_TENANT, "src-1"))

    def test_list_is_tenant_scoped_and_ordered_by_capture_then_id(self) -> None:
        later = SourceRecord(
            source_id="b-src",
            tenant_id=TENANT,
            locator="project_sources/notes/b.md",
            checksum="sha256:b",
            captured_on=date(2026, 10, 4),
            access_rule="client-and-red-only",
        )
        self.store.save(later)
        self.store.save(source(source_id="a-src"))
        self.store.save(source(source_id="other", tenant_id=OTHER_TENANT))

        listed = self.store.list(TENANT)

        self.assertEqual(["a-src", "b-src"], [item.source_id for item in listed])

    def test_a_different_body_under_the_same_id_is_refused(self) -> None:
        self.store.save(source())

        with self.assertRaises(SourceRecordImmutableError):
            self.store.save(source(checksum="sha256:rewritten"))

    def test_resaving_the_identical_source_is_idempotent(self) -> None:
        stored = source()
        self.store.save(stored)

        self.store.save(stored)

        self.assertEqual(stored, self.store.get(TENANT, "src-1"))

    def test_an_unscoped_read_is_refused(self) -> None:
        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(UnscopedSourceRecordError):
                    self.store.list(tenant)
                with self.assertRaises(UnscopedSourceRecordError):
                    self.store.get(tenant, "src-1")


class SourceRecordMapperTests(unittest.TestCase):
    def test_a_source_round_trips_exactly(self) -> None:
        stored = source()

        self.assertEqual(stored, source_from_payload(source_to_payload(stored)))

    def test_a_payload_the_domain_would_reject_raises(self) -> None:
        payload = source_to_payload(source())
        payload["checksum"] = ""

        with self.assertRaises(ValueError):
            source_from_payload(payload)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresSourceRecordStoreTests(unittest.TestCase):
    """The port contract, exercised against the real PostgreSQL schema."""

    @classmethod
    def setUpClass(cls) -> None:
        from alembic import command
        from alembic.config import Config

        cls._psycopg = importlib.import_module("psycopg")
        config = Config(str(REPO_ROOT / "alembic.ini"))
        config.set_main_option(
            "script_location",
            str(REPO_ROOT / "backend/redops/shared/persistence/migrations"),
        )
        config.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(config, "head")
        cls._connection = cls._psycopg.connect(DATABASE_URL)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._connection.close()

    def setUp(self) -> None:
        from redops.contexts.knowledge.infrastructure.repositories import (
            PostgresSourceRecordStore,
        )

        self.repository = PostgresSourceRecordStore(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE source_records RESTART IDENTITY")
        self._connection.commit()

    def test_a_source_survives_a_reload_with_its_checksum(self) -> None:
        stored = source()
        self.repository.save(stored)

        reloaded = self.repository.get(TENANT, "src-1")

        self.assertEqual(stored, reloaded)
        self.assertEqual("sha256:abc", reloaded.checksum)

    def test_a_different_body_under_the_same_id_is_refused(self) -> None:
        self.repository.save(source())

        with self.assertRaises(SourceRecordImmutableError):
            self.repository.save(source(checksum="sha256:rewritten"))

    def test_a_source_is_not_read_back_for_another_client(self) -> None:
        self.repository.save(source())

        self.assertIsNone(self.repository.get(OTHER_TENANT, "src-1"))
        self.assertEqual((), self.repository.list(OTHER_TENANT))

    def test_a_blank_tenant_is_refused(self) -> None:
        with self.assertRaises(UnscopedSourceRecordError):
            self.repository.list("")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

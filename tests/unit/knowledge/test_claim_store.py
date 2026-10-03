"""Behavioral tests for the claim store (Knowledge application).

Rules under test come from SPEC.md sections 3, 4, 9 and 11:
- A claim's provenance may change only through an append-only revision, so a
  same-id re-statement that rewrites the statement or drops recorded revisions
  is refused (sections 3 and 4).
- A claim is a client resource: every read and write carries ``tenant_id``, and
  one client's claims cannot be read for another (sections 3 and 9).
- Source attribution survives ingestion, so a reloaded claim keeps its
  provenance, citations and revision history (section 11).

The durable PostgreSQL case skips cleanly when no psycopg, alembic or
``DATABASE_URL`` is present:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/knowledge/test_claim_store.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.knowledge.domain.entities import Claim
from redops.contexts.knowledge.domain.errors import (
    ClaimConflictError,
    InvalidClaimError,
    UnscopedClaimError,
)
from redops.contexts.knowledge.domain.value_objects import (
    ProvenanceClass,
    SourceCitation,
)
from redops.contexts.knowledge.infrastructure.mappers import (
    claim_from_payload,
    claim_to_payload,
)
from redops.contexts.knowledge.infrastructure.repositories import (
    InMemoryClaimStore,
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


def citation(source_id: str = "src-1", checksum: str = "sha256:abc"):
    return SourceCitation(
        source_id=source_id, checksum=checksum, location="notes/01.md#p1"
    )


def claim(
    claim_id: str = "claim-1",
    tenant_id: str = TENANT,
    statement: str = "the market cares about agency",
    provenance: ProvenanceClass = ProvenanceClass.UNKNOWN,
    citations: frozenset[SourceCitation] = frozenset(),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        tenant_id=tenant_id,
        statement=statement,
        provenance=provenance,
        citations=citations,
        confidence_note="interview notes, low confidence",
    )


class InMemoryClaimStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryClaimStore()

    def test_a_saved_claim_is_resolved_by_claim_id(self) -> None:
        stored = claim()

        self.store.save(stored)

        self.assertEqual(stored, self.store.get(TENANT, "claim-1"))

    def test_an_unknown_claim_resolves_to_none(self) -> None:
        self.store.save(claim())

        self.assertIsNone(self.store.get(TENANT, "missing"))
        self.assertIsNone(self.store.get(OTHER_TENANT, "claim-1"))

    def test_list_is_tenant_scoped_and_ordered_by_id(self) -> None:
        self.store.save(claim(claim_id="b-claim"))
        self.store.save(claim(claim_id="a-claim"))
        self.store.save(claim(claim_id="other", tenant_id=OTHER_TENANT))

        listed = self.store.list(TENANT)

        self.assertEqual(["a-claim", "b-claim"], [item.claim_id for item in listed])

    def test_a_reclassification_is_persisted_with_its_revision(self) -> None:
        stored = claim()
        self.store.save(stored)
        promoted = stored.reclassify(
            provenance=ProvenanceClass.KNOWN,
            actor="red-principal",
            rationale="confirmed against the call transcript",
            on=ON,
            correlation_id="corr-1",
            citations=frozenset({citation()}),
        )

        self.store.save(promoted)

        reloaded = self.store.get(TENANT, "claim-1")
        self.assertEqual(ProvenanceClass.KNOWN, reloaded.provenance)
        self.assertEqual(1, len(reloaded.revisions))
        self.assertEqual("corr-1", reloaded.revisions[0].correlation_id)

    def test_rewriting_a_stored_statement_is_refused(self) -> None:
        self.store.save(claim())

        with self.assertRaises(ClaimConflictError):
            self.store.save(claim(statement="a different assertion"))

    def test_dropping_a_recorded_revision_is_refused(self) -> None:
        stored = claim()
        self.store.save(stored)
        promoted = stored.reclassify(
            provenance=ProvenanceClass.KNOWN,
            actor="red-principal",
            rationale="confirmed",
            on=ON,
            correlation_id="corr-1",
            citations=frozenset({citation()}),
        )
        self.store.save(promoted)

        with self.assertRaises(ClaimConflictError):
            # The promoted provenance has no revision history: a silent change.
            self.store.save(
                claim(
                    provenance=ProvenanceClass.KNOWN,
                    citations=frozenset({citation()}),
                )
            )

    def test_resaving_the_identical_claim_is_idempotent(self) -> None:
        stored = claim()
        self.store.save(stored)

        self.store.save(stored)

        self.assertEqual(stored, self.store.get(TENANT, "claim-1"))

    def test_an_unscoped_read_is_refused(self) -> None:
        for tenant in ("", "   "):
            with self.subTest(tenant=tenant):
                with self.assertRaises(UnscopedClaimError):
                    self.store.list(tenant)
                with self.assertRaises(UnscopedClaimError):
                    self.store.get(tenant, "claim-1")

    def test_an_unscoped_write_is_refused_by_the_domain(self) -> None:
        # The domain refuses to build an unscoped claim before the store sees it.
        with self.assertRaises(InvalidClaimError):
            self.store.save(claim(tenant_id=""))


class ClaimMapperTests(unittest.TestCase):
    def test_a_claim_round_trips_exactly(self) -> None:
        stored = claim(
            provenance=ProvenanceClass.KNOWN,
            citations=frozenset({citation()}),
        )

        self.assertEqual(stored, claim_from_payload(claim_to_payload(stored)))

    def test_a_reclassified_claim_round_trips_its_history(self) -> None:
        promoted = claim().reclassify(
            provenance=ProvenanceClass.KNOWN,
            actor="red-principal",
            rationale="confirmed",
            on=ON,
            correlation_id="corr-1",
            citations=frozenset({citation()}),
        )

        reloaded = claim_from_payload(claim_to_payload(promoted))

        self.assertEqual(promoted, reloaded)
        self.assertEqual(1, len(reloaded.revisions))

    def test_a_payload_the_domain_would_reject_raises(self) -> None:
        payload = claim_to_payload(claim())
        payload["provenance"] = "known"

        with self.assertRaises(ValueError):
            claim_from_payload(payload)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresClaimStoreTests(unittest.TestCase):
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
            PostgresClaimStore,
        )

        self.repository = PostgresClaimStore(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE claims RESTART IDENTITY")
        self._connection.commit()

    def test_a_claim_survives_a_reload_with_its_provenance(self) -> None:
        stored = claim(
            provenance=ProvenanceClass.KNOWN,
            citations=frozenset({citation()}),
        )
        self.repository.save(stored)

        reloaded = self.repository.get(TENANT, "claim-1")

        self.assertEqual(stored, reloaded)
        self.assertEqual(ProvenanceClass.KNOWN, reloaded.provenance)

    def test_a_reclassification_survives_a_reload(self) -> None:
        stored = claim()
        self.repository.save(stored)
        promoted = stored.reclassify(
            provenance=ProvenanceClass.KNOWN,
            actor="red-principal",
            rationale="confirmed",
            on=ON,
            correlation_id="corr-1",
            citations=frozenset({citation()}),
        )
        self.repository.save(promoted)

        reloaded = self.repository.get(TENANT, "claim-1")

        self.assertEqual(1, len(reloaded.revisions))

    def test_rewriting_a_stored_statement_is_refused(self) -> None:
        self.repository.save(claim())

        with self.assertRaises(ClaimConflictError):
            self.repository.save(claim(statement="a different assertion"))

    def test_a_claim_is_not_read_back_for_another_client(self) -> None:
        self.repository.save(claim())

        self.assertIsNone(self.repository.get(OTHER_TENANT, "claim-1"))
        self.assertEqual((), self.repository.list(OTHER_TENANT))

    def test_a_blank_tenant_is_refused(self) -> None:
        with self.assertRaises(UnscopedClaimError):
            self.repository.list("")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

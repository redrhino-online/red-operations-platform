"""Adapter contract tests for the PostgreSQL ``AuthorityAmplifierRepository``.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresAuthorityAmplifierRepository`` against the local compose database: the
schema is created by the committed migration ``0006_authority_amplifiers``
(SPEC.md section 6: migrations committed with schema changes), and an approved
amplifier saved through the adapter is persisted and reloaded as an aggregate
with its grounding message, canonical script, visual package and both approvals
(SPEC.md sections 3 and 4).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/production/test_authority_amplifier_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from pathlib import Path

from redops.contexts.production.domain.errors import (
    AuthorityAmplifierReadinessError,
    AuthorityAmplifierVersionConflictError,
    AuthorityAmplifierVersionTenantBoundaryError,
)

from .fixtures import (
    TENANT,
    approved_amplifier,
    script_approved_amplifier,
)

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresAuthorityAmplifierRepositoryTests(unittest.TestCase):
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
        from redops.contexts.production.infrastructure.repositories import (
            PostgresAuthorityAmplifierRepository,
        )

        self.repository = PostgresAuthorityAmplifierRepository(
            self._connection
        )
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE authority_amplifiers RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.production.infrastructure.repositories import (
            PostgresAuthorityAmplifierRepository,
            authority_amplifier_repository_from_env,
        )

        repository = authority_amplifier_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(
                repository, PostgresAuthorityAmplifierRepository
            )
            self.assertIsNone(repository.get(TENANT, "amplifier-3f"))
        finally:
            repository.close()

    def test_an_approved_amplifier_survives_a_reload(self):
        amplifier = approved_amplifier()
        self.repository.save(amplifier)

        reloaded = self.repository.get(TENANT, amplifier.amplifier_id)

        self.assertEqual(amplifier, reloaded)
        self.assertTrue(reloaded.is_approved)
        self.assertTrue(reloaded.message.is_approved)
        self.assertIsNotNone(reloaded.visuals)

    def test_an_unknown_amplifier_resolves_to_none(self):
        self.repository.save(approved_amplifier())

        self.assertIsNone(self.repository.get(TENANT, "amplifier-other"))

    def test_re_saving_the_identical_amplifier_is_idempotent(self):
        amplifier = approved_amplifier()
        self.repository.save(amplifier)

        self.repository.save(amplifier)

        self.assertEqual(
            amplifier,
            self.repository.get(TENANT, amplifier.amplifier_id),
        )

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(approved_amplifier())

        with self.assertRaises(AuthorityAmplifierVersionConflictError):
            self.repository.save(
                approved_amplifier(owner="a different owner")
            )

    def test_an_amplifier_without_creative_acceptance_cannot_be_stored(self):
        with self.assertRaises(AuthorityAmplifierReadinessError):
            self.repository.save(script_approved_amplifier())

    def test_an_amplifier_is_not_read_back_for_another_client(self):
        self.repository.save(approved_amplifier())

        self.assertIsNone(
            self.repository.get("client-other", "amplifier-3f")
        )

    def test_a_blank_tenant_is_refused_on_read(self):
        with self.assertRaises(AuthorityAmplifierVersionTenantBoundaryError):
            self.repository.get("", "amplifier-3f")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

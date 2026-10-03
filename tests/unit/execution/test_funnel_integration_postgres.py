"""Adapter contract tests for the PostgreSQL ``FunnelIntegrationRepository``.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresFunnelIntegrationRepository`` against the local compose database: the
schema is created by the committed migration ``0007_funnel_integrations``
(SPEC.md section 6: migrations committed with schema changes), and a completed
funnel saved through the adapter is persisted and reloaded as an aggregate with
its grounding amplifier, its thirteen asset references and its pinned prospect
path dry run (SPEC.md sections 3 and 4).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/execution/test_funnel_integration_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from pathlib import Path

from redops.contexts.execution.domain.errors import (
    FunnelReadinessError,
    FunnelVersionConflictError,
    FunnelVersionTenantBoundaryError,
)

from .fixtures import (
    TENANT,
    complete_funnel,
    funnel_integration,
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
class PostgresFunnelIntegrationRepositoryTests(unittest.TestCase):
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
        from redops.contexts.execution.infrastructure.repositories import (
            PostgresFunnelIntegrationRepository,
        )

        self.repository = PostgresFunnelIntegrationRepository(
            self._connection
        )
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE funnel_integrations RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.execution.infrastructure.repositories import (
            PostgresFunnelIntegrationRepository,
            funnel_integration_repository_from_env,
        )

        repository = funnel_integration_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(
                repository, PostgresFunnelIntegrationRepository
            )
            self.assertIsNone(repository.get(TENANT, "funnel-3f"))
        finally:
            repository.close()

    def test_a_complete_funnel_survives_a_reload(self):
        funnel = complete_funnel()
        self.repository.save(funnel)

        reloaded = self.repository.get(TENANT, funnel.integration_id)

        self.assertEqual(funnel, reloaded)
        self.assertTrue(reloaded.is_complete)
        self.assertTrue(reloaded.amplifier.is_approved)
        self.assertTrue(reloaded.dry_run.is_complete)

    def test_an_unknown_funnel_resolves_to_none(self):
        self.repository.save(complete_funnel())

        self.assertIsNone(self.repository.get(TENANT, "funnel-other"))

    def test_re_saving_the_identical_funnel_is_idempotent(self):
        funnel = complete_funnel()
        self.repository.save(funnel)

        self.repository.save(funnel)

        self.assertEqual(
            funnel,
            self.repository.get(TENANT, funnel.integration_id),
        )

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(complete_funnel())

        with self.assertRaises(FunnelVersionConflictError):
            self.repository.save(complete_funnel(owner="a different owner"))

    def test_a_funnel_without_completion_cannot_be_stored(self):
        with self.assertRaises(FunnelReadinessError):
            self.repository.save(funnel_integration())

    def test_a_funnel_is_not_read_back_for_another_client(self):
        self.repository.save(complete_funnel())

        self.assertIsNone(self.repository.get("client-other", "funnel-3f"))

    def test_a_blank_tenant_is_refused_on_read(self):
        with self.assertRaises(FunnelVersionTenantBoundaryError):
            self.repository.get("", "funnel-3f")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

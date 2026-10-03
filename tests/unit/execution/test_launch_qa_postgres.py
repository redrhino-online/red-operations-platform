"""Adapter contract tests for the PostgreSQL ``LaunchQARepository``.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresLaunchQARepository`` against the local compose database: the schema is
created by the committed migration ``0008_launch_qas`` (SPEC.md section 6:
migrations committed with schema changes), and an authorized QA saved through the
adapter is persisted and reloaded as an aggregate with its grounded stage 8
funnel, its sixteen-check evidence, its compliance package and its pinned traffic
authorization (SPEC.md sections 3 and 4).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/execution/test_launch_qa_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from pathlib import Path

from redops.contexts.execution.domain.errors import (
    LaunchQAReadinessError,
    LaunchQAVersionConflictError,
    LaunchQAVersionTenantBoundaryError,
)

from .fixtures import TENANT, launch_qa, ready_for_traffic

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
class PostgresLaunchQARepositoryTests(unittest.TestCase):
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
            PostgresLaunchQARepository,
        )

        self.repository = PostgresLaunchQARepository(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE launch_qas RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.execution.infrastructure.repositories import (
            PostgresLaunchQARepository,
            launch_qa_repository_from_env,
        )

        repository = launch_qa_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(repository, PostgresLaunchQARepository)
            self.assertIsNone(repository.get(TENANT, "qa-3f"))
        finally:
            repository.close()

    def test_an_authorized_qa_survives_a_reload(self):
        qa = ready_for_traffic()
        self.repository.save(qa)

        reloaded = self.repository.get(TENANT, qa.qa_id)

        self.assertEqual(qa, reloaded)
        self.assertTrue(reloaded.is_ready_for_traffic)
        self.assertTrue(reloaded.funnel.is_complete)
        self.assertEqual(qa.compliance, reloaded.compliance)
        self.assertEqual(qa.authorization, reloaded.authorization)

    def test_an_unknown_qa_resolves_to_none(self):
        self.repository.save(ready_for_traffic())

        self.assertIsNone(self.repository.get(TENANT, "qa-other"))

    def test_re_saving_the_identical_qa_is_idempotent(self):
        qa = ready_for_traffic()
        self.repository.save(qa)

        self.repository.save(qa)

        self.assertEqual(qa, self.repository.get(TENANT, qa.qa_id))

    def test_a_different_body_under_the_same_id_is_refused(self):
        self.repository.save(ready_for_traffic())

        with self.assertRaises(LaunchQAVersionConflictError):
            self.repository.save(ready_for_traffic(owner="a different owner"))

    def test_a_qa_without_traffic_authorization_cannot_be_stored(self):
        with self.assertRaises(LaunchQAReadinessError):
            self.repository.save(launch_qa())

    def test_a_qa_is_not_read_back_for_another_client(self):
        self.repository.save(ready_for_traffic())

        self.assertIsNone(self.repository.get("client-other", "qa-3f"))

    def test_a_blank_tenant_is_refused_on_read(self):
        with self.assertRaises(LaunchQAVersionTenantBoundaryError):
            self.repository.get("", "qa-3f")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

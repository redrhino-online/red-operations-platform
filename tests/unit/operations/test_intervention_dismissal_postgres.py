"""Adapter contract tests for the PostgreSQL intervention dismissal store.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresInterventionDismissalRepository`` against the local compose database:
the schema is created by the committed migration ``0016_intervention_dismissals``
(SPEC.md section 6), and an operator dismissal saved through the adapter is
persisted and reloaded as a value object with its tenant, client, card key,
rationale, actor and date (SPEC.md sections 7 and 9).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter still runs the rest of the suite.
Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/operations/test_intervention_dismissal_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.operations.domain.value_objects import (
    InterventionDismissal,
    InterventionReason,
)

TENANT = "tenant-3f"
OTHER_TENANT = "tenant-other"
CLIENT = "engagement-3f"
DISMISSED_ON = date(2026, 10, 3)
DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)


def dismissal(**overrides) -> InterventionDismissal:
    values = {
        "tenant_id": TENANT,
        "client": CLIENT,
        "reason": InterventionReason.BLOCKED_CRITICAL_PATH,
        "subject": "stage-3",
        "rationale": "the blocker is being handled off-platform",
        "actor": "production-manager",
        "dismissed_on": DISMISSED_ON,
    }
    values.update(overrides)
    return InterventionDismissal(**values)


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresInterventionDismissalRepositoryTests(unittest.TestCase):
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
        from redops.contexts.operations.infrastructure.repositories import (
            PostgresInterventionDismissalRepository,
        )

        self.repository = PostgresInterventionDismissalRepository(
            self._connection
        )
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE intervention_dismissals RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.operations.infrastructure.repositories import (
            PostgresInterventionDismissalRepository,
            intervention_dismissal_repository_from_env,
        )

        repository = intervention_dismissal_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(
                repository, PostgresInterventionDismissalRepository
            )
            self.assertEqual((), repository.list(TENANT, CLIENT))
        finally:
            repository.close()

    def test_a_dismissal_survives_a_reload(self) -> None:
        stored = dismissal()
        self.repository.save(stored)

        self.assertEqual((stored,), self.repository.list(TENANT, CLIENT))

    def test_a_same_key_different_body_is_refused(self) -> None:
        from redops.contexts.operations.domain.errors import (
            InterventionDismissalConflictError,
        )

        self.repository.save(dismissal())

        with self.assertRaises(InterventionDismissalConflictError):
            self.repository.save(dismissal(rationale="a different reason"))

    def test_list_returns_only_the_tenant_and_client_dismissals(self) -> None:
        self.repository.save(dismissal(subject="stage-3"))
        self.repository.save(dismissal(subject="stage-4"))
        self.repository.save(
            dismissal(tenant_id=OTHER_TENANT, subject="stage-5")
        )

        listed = self.repository.list(TENANT, CLIENT)

        self.assertEqual(
            {"stage-3", "stage-4"}, {item.subject for item in listed}
        )
        self.assertEqual(1, len(self.repository.list(OTHER_TENANT, CLIENT)))
        self.assertEqual(
            (), self.repository.list(OTHER_TENANT, "engagement-other")
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

"""Adapter contract tests for the PostgreSQL ``MethodVersionRepository``.

ADR 0003 makes RED's records durable in PostgreSQL, and SPEC.md section 6 says
infrastructure adapters implement ports. These tests exercise the real
``PostgresMethodVersionRepository`` against the local compose database: the
schema is created by the committed migration ``0003_method_versions`` (SPEC.md
section 6: migrations committed with schema changes), and an approved method
saved through the adapter is persisted and reloaded as an aggregate with its
exact semantic version, its approval and its pinned dependencies (SPEC.md
sections 3 and 4).

They skip cleanly when no psycopg driver, no alembic or no ``DATABASE_URL`` is
present, so the domain-only test interpreter (Python 3.10, no third-party
packages) still runs the rest of the suite. Run them with the app environment:

    export DATABASE_URL=postgresql://redops:redops@localhost:5432/redops
    PYTHONPATH=backend python -m pytest tests/unit/method/test_method_version_postgres.py -q
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import unittest
from datetime import date
from pathlib import Path

from redops.contexts.method.domain.errors import (
    MethodApprovalError,
    MethodVersionConflictError,
    MethodVersionTenantBoundaryError,
)
from redops.contexts.method.domain.value_objects import SemanticVersion

from .test_method_version import method_version

DATABASE_URL = os.environ.get("DATABASE_URL")
REPO_ROOT = Path(__file__).resolve().parents[3]
HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None
HAS_ALEMBIC = importlib.util.find_spec("alembic") is not None
RUN = bool(DATABASE_URL) and HAS_PSYCOPG and HAS_ALEMBIC
SKIP_REASON = (
    "PostgreSQL adapter test requires DATABASE_URL, psycopg and alembic; "
    "export DATABASE_URL and install the app dependencies to run it"
)

TENANT = "client-3f"
ON = date(2026, 10, 2)


def approved_method(method=None):
    return (method or method_version()).approve(
        approved_by="client-approver-1",
        intended_use="3f pilot campaign",
        on=ON,
    )


@unittest.skipUnless(RUN, SKIP_REASON)
class PostgresMethodVersionRepositoryTests(unittest.TestCase):
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
        from redops.contexts.method.infrastructure.repositories import (
            PostgresMethodVersionRepository,
        )

        self.repository = PostgresMethodVersionRepository(self._connection)
        self._connection.rollback()
        with self._connection.cursor() as cursor:
            cursor.execute("TRUNCATE method_versions RESTART IDENTITY")
        self._connection.commit()

    def test_the_factory_builds_the_postgres_adapter_from_a_database_url(
        self,
    ) -> None:
        from redops.contexts.method.infrastructure.repositories import (
            PostgresMethodVersionRepository,
            method_version_repository_from_env,
        )

        repository = method_version_repository_from_env(DATABASE_URL)
        try:
            self.assertIsInstance(repository, PostgresMethodVersionRepository)
            self.assertIsNone(
                repository.get(TENANT, "method-3f", SemanticVersion(1, 0, 0))
            )
        finally:
            repository.close()

    def test_an_approved_method_survives_a_reload_with_its_approval(self):
        method = approved_method()
        self.repository.save(method)

        reloaded = self.repository.get(
            TENANT, "method-3f", method.semantic_version
        )

        self.assertEqual(method, reloaded)
        self.assertEqual("client-approver-1", reloaded.approval.approved_by)
        self.assertEqual("3f pilot campaign", reloaded.approval.intended_use)

    def test_an_unknown_version_resolves_to_none(self):
        self.repository.save(approved_method())

        self.assertIsNone(
            self.repository.get(TENANT, "method-3f", SemanticVersion(2, 0, 0))
        )

    def test_re_saving_the_identical_method_is_idempotent(self):
        method = approved_method()
        self.repository.save(method)

        self.repository.save(method)

        self.assertEqual(
            method,
            self.repository.get(TENANT, "method-3f", method.semantic_version),
        )

    def test_a_different_body_under_the_same_version_is_refused(self):
        self.repository.save(approved_method())

        with self.assertRaises(MethodVersionConflictError):
            self.repository.save(
                approved_method(method_version(currency="monthly-revenue"))
            )

    def test_an_unapproved_draft_cannot_be_stored(self):
        with self.assertRaises(MethodApprovalError):
            self.repository.save(method_version())

    def test_a_method_is_not_read_back_for_another_client(self):
        self.repository.save(approved_method())

        self.assertIsNone(
            self.repository.get(
                "client-other", "method-3f", SemanticVersion(1, 0, 0)
            )
        )

    def test_a_blank_tenant_is_refused_on_read(self):
        with self.assertRaises(MethodVersionTenantBoundaryError):
            self.repository.get("", "method-3f", SemanticVersion(1, 0, 0))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
